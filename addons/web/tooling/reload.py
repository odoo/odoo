#!/usr/bin/env python

import subprocess
import helpers

community = helpers.get_community_path()
tooling = helpers.get_tooling_path()

# Call disable.py and enable.py scripts
subprocess.run(["python", str(tooling / "disable.py")], check=True)
subprocess.run(["python", str(tooling / "enable.py")], check=True)
