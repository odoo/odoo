#!/usr/bin/env python

import helpers

community = helpers.get_community_path()

enterprise_dir, _ = helpers.prompt_for_enterprise_action(community)

helpers.disable_in_dir(community)

if enterprise_dir:
    helpers.disable_in_dir(enterprise_dir)

print("\nJS tooling have been removed from the roots\n")
