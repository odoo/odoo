#!/usr/bin/env python

import json
import argparse
from pathlib import Path
import helpers
import os

def generate_jsconfig(addon_paths = [], exclude_paths = []):
    config = {
        "compilerOptions": {
            "moduleResolution": "node",
            "baseUrl": ".",
            "target": "ES2022",
            "noEmit": True,
            "disableSizeLimit": True,
            "typeRoots": ["addons/web/tooling/types"],
            "paths": addon_paths
        },
        "include": ["**/*.js", "**/*.ts"],
        "exclude": exclude_paths
    }
    return config

def merge_configs(default_config_path = "default-config.json", custom_config_path = "custom-config.json"):
    """
    Merge two JSON configuration files.
    The values in the custom configuration will overwrite the values in the default configuration.
    If the value is a list, the lists will be concatenated.

    Args:
        default_config_path (str): Path to the default configuration file.
        custom_config_path (str): Path to the custom configuration file.

    Returns:
        dict: A dictionary that represents the merged configuration.
    """
    default_config = read_json_file(Path(helpers.get_tooling_path() / default_config_path))
    
    if custom_config_path is None or not Path(custom_config_path).exists():
        print("No custom tooling config file found. Using default config.")
        return default_config

    custom_config = read_json_file(Path(helpers.get_tooling_path() /custom_config_path))

    # Merge the dictionaries. The values in the second dictionary will overwrite those in the first.
    # If the value is a list, the lists will be concatenated.
    merged_config = {}
    for key in set(default_config.keys()).union(custom_config.keys()):
        if isinstance(default_config.get(key), list) and isinstance(custom_config.get(key), list):
            merged_config[key] = default_config[key] + custom_config[key]
        else:
            merged_config[key] = custom_config.get(key, default_config.get(key))

    return merged_config

def read_json_file(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

def save_json_to_file(config, filename):
    with open(filename, 'w') as file:
        json.dump(config, file, indent=4)

def add_module_to_dict(module_name, items, path_prefix=None):
    key = f"@{module_name}/*"
    if path_prefix:
        value = str(Path(path_prefix) / module_name / "static" / "src" / "*")
    else:
        value = str(Path(module_name) / "static" / "src" / "*")
    items[key] = [value]

# Define command-line arguments
parser = argparse.ArgumentParser(description='Generate _jsconfig.json.')
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument('--for_community', action='store_true', help='Include community modules.')
group.add_argument('--for_enterprise', action='store_true', help='Include enterprise modules.')
parser.add_argument('--relative_enterprise_path', default="../enterprise", 
                    help='Relative path from community to enterprise.', required=True)
args = parser.parse_args()

tooling_config = merge_configs()
addon_paths = {}

if args.for_community: 
    for module_name in tooling_config["community_modules"]:
        add_module_to_dict(module_name, addon_paths)
        # 'addons' is now a constant string. So, using a string literal instead of a variable.
        add_module_to_dict(module_name, addon_paths, 'addons')
    for module_name in tooling_config["enterprise_modules"]:
        # Remove trailing slashes from the path if any.
        add_module_to_dict(module_name, addon_paths, str(Path(args.relative_enterprise_path)))

if args.for_enterprise: 
    for module_name in tooling_config["community_modules"]:
        # Construct the path using pathlib to ensure it's correct for the current operating system.
        enterprise_relative_path =  os.path.relpath(helpers.get_community_path(),  Path(helpers.get_community_path() / args.relative_enterprise_path).resolve())
        path_prefix = str(Path(enterprise_relative_path) / 'addons')
        add_module_to_dict(module_name, addon_paths, path_prefix)
    for module_name in tooling_config["enterprise_modules"]:
        add_module_to_dict(module_name, addon_paths)

# Generate jsconfig using the constructed addon_paths.
jsconfig = generate_jsconfig(addon_paths)

# Save the generated jsconfig to '_jsconfig.json' file.
save_json_to_file(jsconfig, Path(helpers.get_tooling_path() / '_jsconfig.json'))
