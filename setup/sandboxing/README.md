# Sandboxing AI Coding Assistants

We advise running AI coding assistants in a sandbox for better security and privacy.
These scripts and configurations allow you to run popular AI coding assistants with
filesystem isolation, so the assistant can only access the files it needs to work
on, and not your entire home directory.

Without sandboxing, the AI assistant has access to your entire home directory, including
SSH keys, GPG keys, browser profiles, credentials files, and any other secrets.
Sandboxing restricts the visible filesystem to only the directories the assistant
actually needs.

AI assistants are powerful tools that can execute code, read and write files, and access
the network. Running them without isolation can lead to accidental data leaks or malicious
code execution if the assistant is compromised. By using sandboxing, you can mitigate
these risks while still benefiting from the assistant's capabilities.

## Bubblewrap

These scripts use [bubblewrap](https://github.com/containers/bubblewrap) to run AI
coding assistants with filesystem isolation, no container runtime needed.

All functions of the assistant should work as normal, but the assistant will only see a
limited view of the filesystem. The assistant will be able to edit files in the Odoo
workspace and any other explicitly added directories, but won't be able to access files
outside of those areas. It will also be able to run Python and JavaScript tests.

### Prerequisites

Install bubblewrap with your package manager. For example, on Debian/Ubuntu:

```sh
sudo apt install bubblewrap
```

For Ubuntu 24.04 and later, you also need to load the appropriate AppArmor profile for Bubblewrap:

```sh
sudo apt install apparmor-profiles
sudo ln -s /usr/share/apparmor/extra-profiles/bwrap-userns-restrict /etc/apparmor.d/
sudo apparmor_parser /etc/apparmor.d/bwrap-userns-restrict
```

It is advised to copy the scripts `bwrap-claude.sh` and `bwrap-opencode.sh` to a
directory in your PATH (e.g. `~/.local/bin`).

Both scripts pre-mount the Odoo workspace directory. By default, it is defined to `~/src/odoo`,
meaning that the workspace should contain the directories `~/src/odoo/odoo`,
`~/src/odoo/enterprise` and any other Odoo-related directory (e.g. design-themes).

Override the default path with the environment variable `ODOO_BASE` (e.g.
`ODOO_BASE=~/my/odoo`).

Chrome, PostgreSQL, and the Odoo filestore are mounted opportunistically with
`bind-try` and silently skipped when absent.

### bwrap-opencode.sh

Sandbox wrapper for [Opencode](https://opencode.ai).

Install Opencode as recommended by the documentation:
```sh
curl -fsSL https://opencode.ai/install | bash
```

Then, launch the sandboxed Opencode:

```sh
# Odoo dirs are pre-mounted, so no args needed for basic usage
bwrap-opencode.sh [opencode args...]

# Mount extra directories beyond Odoo
bwrap-opencode.sh --add-dir ~/src/my-project [opencode args...]
```

`--add-dir` paths are bind-mounted read-write into the sandbox. Opencode does not
support `--add-dir` natively, so these flags are consumed by the wrapper and **not**
forwarded to the opencode binary.

No IDE integration. See the script header for the full sandbox layout.


### bwrap-claude.sh

Sandbox wrapper for [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

Install Claude Code as recommended by the documentation:
```sh
curl -fsSL https://claude.ai/install.sh | bash
```

Then, launch the sandboxed Claude:

```sh
# Odoo dirs are pre-mounted, so no args needed for basic usage
bwrap-claude.sh [claude args...]

# Mount extra directories beyond Odoo
bwrap-claude.sh --add-dir ~/src/my-project [claude args...]
```

Each `--add-dir` path is bind-mounted read-write **and** passed to Claude's own
`--add-dir` flag, so Claude's tool access matches the sandbox boundary.

For a complete sandboxing with VSCode, configure the
[Claude Code VSCode extension](https://marketplace.visualstudio.com/items?itemName=anthropic.claude-code)
and change the VSCode Claude extension setting
`claudeCode.claudeProcessWrapper` to `bwrap-claude.sh`.

In order to connect VSCode and the sandboxed Claude, type `/ide` in the Claude CLI.
If VSCode is started, it should appear in the Claude CLI output.

See the script header for the full sandbox layout.

#### Using OpenRouter

To use [OpenRouter](https://openrouter.ai/) as a proxy for Claude API calls, set the
`OPENROUTER_API_KEY` environment variable and pass the `--openrouter` flag.

Add the following to your shell configuration (e.g. `~/.bashrc`, `~/.zshrc`, or `~/.config/fish/config.fish`):

```sh
export OPENROUTER_API_KEY="sk-or-xxx"
```

Reload your shell configuration (e.g. `source ~/.bashrc`, `source ~/.zshrc`, or `source ~/.config/fish/config.fish`).
Then launch the sandboxed Claude with:

```sh
bwrap-claude.sh --openrouter
```

The following environment variables are passed to the sandbox with sensible defaults:

| Variable                         | Default                     |
| -------------------------------- | --------------------------- |
| `ANTHROPIC_BASE_URL`             | `https://openrouter.ai/api` |
| `ANTHROPIC_DEFAULT_HAIKU_MODEL`  | `z-ai/glm-4.7-flash`        |
| `ANTHROPIC_DEFAULT_SONNET_MODEL` | `z-ai/glm-5-turbo`          |
| `ANTHROPIC_DEFAULT_OPUS_MODEL`   | `z-ai/glm-5`                |

Override any default by exporting the corresponding environment variable:

```sh
export ANTHROPIC_DEFAULT_OPUS_MODEL="minimax/minimax-m2.7"
bwrap-claude.sh --openrouter
```

### Example: Running Odoo tests

Here is an example of prompt to run the CRM tests (Python and JavaScript tours):

```
Here is how to initialize a DB named "pouet" :
~/src/odoo/odoo/odoo-bin --addons-path=~/src/odoo/enterprise,~/src/odoo/odoo/addons -d pouet -i base --stop-after-init --logfile=~/src/odoo/log/pouet.log

Then, install the CRM module:
~/src/odoo/odoo/odoo-bin --addons-path=~/src/odoo/enterprise,~/src/odoo/odoo/addons -d pouet -i crm --stop-after-init --logfile=~/src/odoo/log/pouet.log

Finally, run the tests for the CRM module:
~/src/odoo/odoo/odoo-bin --addons-path=~/src/odoo/enterprise,~/src/odoo/odoo/addons -d pouet -u crm --test-enable --logfile=~/src/odoo/log/pouet.log

Can you do this for me?
```

You can follow the logs in the file `~/src/odoo/log/pouet.log`.

### Troubleshooting

1. If you get the following error:

```
bwrap: setting up uid map: Permission denied
```

Make sure you loaded the AppArmor profile for Bubblewrap as described in the prerequisites.
This is required on Ubuntu 24.04 and later.

Another solution is to deactivate the user namespace restrictions in AppArmor, but this is
less secure:

```sh
sudo sysctl -w kernel.apparmor_restrict_unprivileged_unconfined=0
sudo sysctl -w kernel.apparmor_restrict_unprivileged_userns=0
```
