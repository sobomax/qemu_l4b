from ast import literal_eval
from os import walk as o_walk
import re
from sys import stderr, argv, exit as s_exit
from os.path import dirname, join as p_join, abspath, isdir
from subprocess import check_output


class StructDefFinder:
    def __init__(self, config, directory, debug=False, no_header=False):
        structs = config.get("structs", tuple())
        defines = config.get("defines", tuple())
        defs_forcehost = config.get("defines_forcehost", tuple())
        defs_target = config.get("defines_target", tuple())
        str_norecurse = config.get("structs_norecurse", tuple())
        if not any(isinstance(x, (list, tuple)) for x in (structs, defines, defs_forcehost, defs_target, str_norecurse)):
            raise ValueError("'structs' and 'defines' must be lists or tuples.")
        self.defines = defines + defs_forcehost + defs_target
        ddup = tuple(d for d in self.defines if self.defines.count(d) > 1)
        if ddup:
            raise ValueError(f"Duplicate defines: {ddup}")
        self.directory = directory
        self.structs = structs
        self.defs_forcehost = defs_forcehost
        self.defs_target = defs_target
        self.str_norecurse = str_norecurse
        self.debug = debug
        self.no_header = no_header
        self.found_structs = []
        self.found_defines = []

    def find_in_dir(self, structs=None, defines=None, is_top_level=True):
        structs = structs or self.structs
        defines = defines or self.defines
        not_found_structs = set(structs)
        not_found_defines = set(defines)

        for root, _, files in o_walk(self.directory):
            for file in files:
                if not file.endswith('.h'):
                    continue
                path = p_join(root, file)
                if self.debug:
                    print(f"\nSearching in file: {path}", file=stderr)
                try:
                    with open(path, 'r') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    print(f"Warning: '{path}' contains non-ascii characters, ignored", file=stderr)
                    continue

                for s_name in structs:
                    if s_name not in not_found_structs:
                        continue
                    if self.debug:
                        print(f"Looking for struct '{s_name}' in: {path}", file=stderr)
                    pattern = re.compile(r'^struct\s+' + re.escape(s_name) + r'\s*\{(.*?)^\};', re.DOTALL | re.MULTILINE)
                    match = pattern.search(content)
                    if match:
                        if self.debug:
                            print(f"Found struct '{s_name}' in: {path}", file=stderr)
                        self.find_refs_in_file(path, match.group(1), is_top_level=False)
                        self.found_structs.append((s_name, match.group(0), path))
                        not_found_structs.discard(s_name)

                if is_top_level:
                    for d_name in defines:
                        if d_name not in not_found_defines:
                            continue
                        if self.debug:
                            print(f"Looking for #define '{d_name}' in: {path}", file=stderr)
                        pattern = re.compile(r'^#\s*define\s+' + re.escape(d_name) + r'([\s(](?:[^\n]*\\\n)*[^\n]*)', re.MULTILINE)
                        match = pattern.search(content)
                        if match:
                            if self.debug:
                                print(f"Found #define '{d_name}' in: {path}", file=stderr)
                            self.found_defines.append((d_name, match.group(1), path))
                            not_found_defines.discard(d_name)

        if is_top_level:
            if not_found_structs:
                print(f"Error: Structs not found: {', '.join(not_found_structs)}", file=stderr)
            if not_found_defines:
                print(f"Error: Defines not found: {', '.join(not_found_defines)}", file=stderr)
            if not_found_structs or not_found_defines:
                s_exit(1)

    def find_refs_in_file(self, path, struct_body, is_top_level):
        refs = re.findall(r'struct\s+(\w+)', struct_body)
        if self.debug:
            print(f"Referenced structs in '{path}': {refs}", file=stderr)
        with open(path, 'r') as f:
            content = f.read()
            for ref in refs:
                if not any(ref == found[0] for found in self.found_structs):
                    if self.debug:
                        print(f"Searching for '{ref}' in same file '{path}'", file=stderr)
                    pattern = re.compile(r'struct\s+' + re.escape(ref) + r'\s*\{([^\}]*)\}\s*;', re.DOTALL)
                    match = pattern.search(content)
                    if match:
                        self.find_refs_in_file(path, match.group(1), is_top_level=False)
                        self.found_structs.append((ref, match.group(0), path))
                    else:
                        if not is_top_level:
                            print(f"Warning: '{ref}' not found in '{path}'", file=stderr)
        self.find_refs(struct_body)

    def find_refs(self, struct_body):
        refs = re.findall(r'struct\s+(\w+)', struct_body)
        if self.debug:
            print(f"Referenced structs in other files: {refs}", file=stderr)
        for ref in (r for r in refs if r not in self.str_norecurse):
            if not any(ref == found[0] for found in self.found_structs):
                if self.debug:
                    print(f"Recursively searching for '{ref}' in other files", file=stderr)
                self.find_in_dir(structs=[ref], defines=[], is_top_level=False)

    def get_git_info(self):
        path = abspath(self.directory)
        while path != "/":
            git_dir = p_join(path, ".git")
            if isdir(git_dir):
                try:
                    rev = check_output(["git", "rev-parse", "HEAD"], cwd=path).decode().strip()
                    branch = check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=path).decode().strip()
                    return (rev, branch)
                except Exception as e:
                    print(f"Warning: Unable to get git info: {e}", file=stderr)
                break
            path = dirname(path)
        return None

    def sort_found_structs(self):
        r = tuple(s for s in self.found_structs if s[0] not in self.structs)
        r += tuple(next(_s for _s in self.found_structs if _s[0] == sn) for sn in self.structs)
        return r

    def print_results(self):
        if not self.found_structs and not self.found_defines:
            print("\nNo structs or defines found.", file=stderr)
            return
        strip_at = len(dirname(self.directory)) + 1
        s_path = lambda p: p[strip_at:]
        if not self.no_header:
            gi = self.get_git_info()
            print(f"#pragma once /* Auto generated by: {' '.join(argv)} */")
            if gi is not None:
                rev, branch = gi
                print(f"/* From Git revision: {rev} branch: {branch} */")
        print_structs = self.sort_found_structs()
        if print_structs:
            print("\n/* Forward declarations: */")
            decls = tuple(f"struct {name};" for name, _, _ in print_structs)
            for decl in decls:
                print(decl)
        if self.found_defines:
            print("\n/* Defines: */")
            def get_def(dn, definition):
                return f'#define {dn}{fixup_comments(definition)}'
            def get_tgt(path):
                return f'/* found in: {s_path(path)} */'
            def join_str(*a):
                return '\n'.join(a)
            def get_def_undef(dn, definition, path):
                if dn in self.defs_target:
                    dn = 'TARGET_' + dn
                    undef = join_str(
                        f"#if defined({dn})",
                        f"#undef {dn}",
                        f"#endif {get_tgt(path)}",
                    )
                    return join_str(undef, get_def(dn, definition))
                parts = definition.split("/*")
                hdn = f'HOST_{dn}'
                generate_host = True
                try:
                    literal_eval(parts[0])
                except (SyntaxError, ValueError):
                    generate_host = dn in self.defs_forcehost
                if not generate_host:
                    undef = f"#undef {dn} {get_tgt(path)}"
                else:
                    undef = join_str(
                        f"#if defined({dn}) && !defined({hdn})",
                        f"static const typeof({dn}) {hdn} = {dn};",
                        f"#endif {get_tgt(path)}",
                        f"#undef {dn}",
                    )
                return join_str(undef, get_def(dn, definition))
            for defstr in (get_def_undef(*x) for x in self.found_defines):
                print(defstr)
        if print_structs:
            print("\n/* Struct definitions: */")
            for name, definition, path in print_structs:
                print(f"\n/* '{name}' found in: {s_path(path)} */")
                print(definition)


def fixup_comments(s):
    if '/*' in s and '*/' not in s:
        if s[-1] not in (' ', '\t'):
            s += ' '
        s += '*/'
    return s
