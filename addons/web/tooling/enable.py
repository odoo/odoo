#!/usr/bin/env python

import helpers

community = helpers.get_community_path()
tooling = helpers.get_tooling_path()

enterprise_dir, relative_path = helpers.prompt_for_enterprise_action(community)

helpers.generate_jsconfig(for_community=True, relative_enterprise_path=relative_path)
helpers.enable_in_dir(community, tooling)

if enterprise_dir:
    helpers.generate_jsconfig(for_enterprise=True, relative_enterprise_path=relative_path)
    helpers.enable_in_dir(enterprise_dir, tooling, copy_mode=True)

print("\n")
print("JS tooling have been enabled")
print("Make sure to refresh the eslint and typescript service and configure your IDE so it uses the config files")
print("For any customisation, copy custom-config.jsonc.example to custom-config.json in community/addons/web/tooling directory (it is git ignored).")
