#!/usr/bin/env python

import helpers

community = helpers.get_community_path()
tooling = helpers.get_tooling_path()

enterprise_dir, _ = helpers.prompt_for_enterprise_action(community)

helpers.refresh_in_dir(community, tooling)

if enterprise_dir:
    helpers.refresh_in_dir(enterprise_dir, tooling)

print("\nThe JS tooling config files have been refreshed")
print("Make sure to refresh the eslint and typescript service and configure your IDE so it uses the config files")
print("Note that if you changed your custom-config.json file, you will need to do a tooling full reload instead.")
