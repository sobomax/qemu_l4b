import argparse
from ast import literal_eval
import os
import re
import sys
from os.path import dirname, join as p_join, abspath, isdir
from subprocess import check_output

def find_structs_and_defines_in_directory(directory_path, struct_names, define_names, found_structs, found_defines, debug, is_top_level=True):
    not_found_structs = set(struct_names)
    not_found_defines = set(define_names)

    # Iterate through all files in the directory, including subdirectories
    for root, _, files in os.walk(directory_path):
        for file in files:
            if file.endswith('.h'):
                file_path = p_join(root, file)
                if debug:
                    print("\n" + f"Searching for structs and defines in file: {file_path}", file=sys.stderr)

                # Find struct definitions in the current file
                with open(file_path, 'r') as f:
                    try:
                        content = f.read()
                    except UnicodeDecodeError:
                        print(f"Warning: '{file_path}' contains non-ascii characters, ignored", file=sys.stderr)
                        continue

                for struct_name in struct_names:
                    if struct_name not in not_found_structs:
                        continue
                    if debug:
                        print(f"Searching for struct '{struct_name}' in file: {file_path}", file=sys.stderr)
                    struct_pattern = re.compile(r'struct\s+' + re.escape(struct_name) + r'\s*\{([^\}]*)\}\s*;', re.DOTALL)
                    match = struct_pattern.search(content)
                    if match:
                        if debug:
                            print(f"Found struct '{struct_name}' in file: {file_path}", file=sys.stderr)
                        found_structs.append((struct_name, match.group(0), file_path))
                        not_found_structs.discard(struct_name)
                        find_referenced_structs_in_file(directory_path, file_path, match.group(1), found_structs, debug, is_top_level=False)

                # Find #define definitions in the current file, only if it's a top-level search
                if is_top_level:
                    for define_name in define_names:
                        if define_name not in not_found_defines:
                            continue
                        if debug:
                            print(f"Searching for #define '{define_name}' in file: {file_path}", file=sys.stderr)
                        define_pattern = re.compile(r'#\s*define\s+' + re.escape(define_name) + r'([\s(]+.*)')
                        match = define_pattern.search(content)
                        if match:
                            if debug:
                                print(f"Found #define '{define_name}' in file: {file_path}", file=sys.stderr)
                            #raise Exception(f"{match.group(1)=}")
                            found_defines.append((define_name, match.group(1), file_path))
                            not_found_defines.discard(define_name)

    # Check for any structs or defines that were not found, only if it's a top-level search
    if is_top_level:
        if not_found_structs:
            print(f"Error: The following top-level structs were not found: {', '.join(not_found_structs)}", file=sys.stderr)
        if not_found_defines:
            print(f"Error: The following top-level defines were not found: {', '.join(not_found_defines)}", file=sys.stderr)
        if not_found_structs or not_found_defines:
            sys.exit(1)

def find_referenced_structs_in_file(directory_path, file_path, struct_body, found_structs, debug, is_top_level):
    referenced_structs = re.findall(r'struct\s+(\w+)', struct_body)
    if debug:
        print(f"Referenced structs in file '{file_path}': {referenced_structs}", file=sys.stderr)
    with open(file_path, 'r') as f:
        content = f.read()
        for ref_struct in referenced_structs:
            if not any(ref_struct == found[0] for found in found_structs):
                if debug:
                    print(f"Searching for referenced struct '{ref_struct}' in the same file '{file_path}'", file=sys.stderr)
                struct_pattern = re.compile(r'struct\s+' + re.escape(ref_struct) + r'\s*\{([^\}]*)\}\s*;', re.DOTALL)
                match = struct_pattern.search(content)
                if match:
                    found_structs.append((ref_struct, match.group(0), file_path))
                    # Recursively search for any structs referenced in this newly found struct
                    find_referenced_structs_in_file(directory_path, file_path, match.group(1), found_structs, debug, is_top_level=False)
                else:
                    if not is_top_level:
                        print(f"Warning: Referenced struct '{ref_struct}' not found in file '{file_path}'", file=sys.stderr)
    # Search other files in the directory for any referenced structs
    find_referenced_structs(directory_path, struct_body, found_structs, debug)

def find_referenced_structs(directory_path, struct_body, found_structs, debug):
    referenced_structs = re.findall(r'struct\s+(\w+)', struct_body)
    if debug:
        print(f"Referenced structs found in other files: {referenced_structs}", file=sys.stderr)
    for ref_struct in referenced_structs:
        if not any(ref_struct == found[0] for found in found_structs):
            if debug:
                print(f"Recursively searching for referenced struct '{ref_struct}' in other files", file=sys.stderr)
            find_structs_and_defines_in_directory(directory_path, [ref_struct], [], found_structs, [], debug, is_top_level=False)

def fixup_comments(str):
    if str.find('/*') == -1 or str.find('*/') != -1:
        return str
    if str[-1] not in (' ', '\t'):
        str += ' '
    str += '*/'
    return str

def main():
    parser = argparse.ArgumentParser(description="Process a directory with an optional config file and debug mode.")
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--no-header', action='store_true', help='Disable header')
    parser.add_argument('directory_path', help='Path to the directory')
    parser.add_argument('config_file', help='Path to the config file')

    args = parser.parse_args()
    directory_path = args.directory_path
    config_file = args.config_file
    debug = args.debug

    # Read struct names and defines from configuration file if provided
    struct_names = []
    define_names = []
    if config_file:
        try:
            with open(config_file, 'r') as f:
                content = f.read()
                config = eval(content)  # Use eval to parse the Python dictionary
                if not isinstance(config, dict):
                    raise ValueError("Configuration file must contain a dictionary.")
                struct_names = config.get("structs", [])
                define_names = config.get("defines", [])
                if not isinstance(struct_names, (list, tuple)) or not isinstance(define_names, (list, tuple)):
                    raise ValueError("'structs' and 'defines' must be lists or tuples in the configuration file.")
        except Exception as e:
            print(f"Error reading configuration file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print("Please provide struct names either via command line or configuration file.", file=sys.stderr)
        sys.exit(1)

    found_structs = []
    found_defines = []

    find_structs_and_defines_in_directory(directory_path, struct_names, define_names, found_structs, found_defines, debug, is_top_level=True)
    print_results(args, found_structs, found_defines)

def get_git_info(directory_path):
    current_path = abspath(directory_path)
    while current_path != "/":
        git_dir = p_join(current_path, ".git")
        if isdir(git_dir):
            try:
                # Get git revision and branch name
                revision = check_output(["git", "rev-parse", "HEAD"], cwd=current_path).decode().strip()
                branch = check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=current_path).decode().strip()
                return (revision, branch)
            except subprocess.CalledProcessError as e:
                print(f"Warning: Unable to retrieve git information: {e}", file=sys.stderr)
            break
        current_path = dirname(current_path)
    return None

def print_results(args, found_structs, found_defines):
    if found_structs or found_defines:
        strip_at = len(dirname(args.directory_path)) + 1
        def s_path(p): return p[strip_at:]
        if not args.no_header:
            gi = get_git_info(args.directory_path)
            print(f"#pragma once /* Auto generated by: {' '.join(sys.argv)} */")
            if gi is not None:
                revision, branch = gi
                print(f"/* From Git revision: {revision} branch: {branch} */")
        if found_structs:
            print("\n/* Forward declarations: */")
            forward_declarations = set()
            for struct_name, _, _ in found_structs:
                forward_declarations.add(f"struct {struct_name};")
            for declaration in forward_declarations:
                print(declaration)

        if found_defines:
            print("\n/* Defines: */")
            for dn, definition, file_path in found_defines:
                p = definition.split("/*")
                hdn = f'HOST_{dn}'
                try:
                    t = literal_eval(p[0])
                except (SyntaxError, ValueError):
                    undef = f"#undef {dn} /* found in: {s_path(file_path)} */"
                else:
                    undef = "\n".join((
                        f"#if defined({dn}) && !defined({hdn})",
                        f"static const typeof({dn}) {hdn} = {dn};",
                        f"#endif /* target found in: {s_path(file_path)} */",
                        f"#undef {dn}",
                    ))
                print(undef)
                defn = fixup_comments(definition)
                print(f"#define {dn}{defn}")

        if found_structs:
            print("\n/* Struct definitions found (from last to first): */")
            for struct_name, struct_definition, file_path in reversed(found_structs):
                print(f"\n/* '{struct_name}' found in: {s_path(file_path)} */")
                print(struct_definition)
    else:
        print(f"\nNo structs or defines found in the specified directory.", file=sys.stderr)

if __name__ == "__main__":
    main()

