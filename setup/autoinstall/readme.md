This folder contains the tools to setup an environment able to run Odoo.

The main goal is to setup an development environment on a debian like system, even if it could also be used for production.


# Usage

To execute this script without downloading it, you can use the following command:

`python3 <(curl https://raw.githubusercontent.com/odoo-dev/odoo/master/setup/autoinstall/autoinstall.py) -a`

Some flags are available, -a will enable all flags, you mays prefer to start without it for a lighter version. You can also use -y for a true silent install, but it is not recommended for the first run as you may want to check what is going to be installed.

```

usage: 63 [-h] [--dry-run] [--interactive] [-y] [-a] [-v] [--default] [--dev] [--opt] [--docker] [--create-config] [--odoo-repo] [--private-repo] [--postgres] [--minimal-packages] [--default-packages] [--dev-packages] [--dev-remote] [--dev-repos] [--chrome] [--pdf]
          [--opt-packages] [--rtlcss] [--git-use-http] [--branch BRANCH]

options:
  -h, --help          show this help message and exit
  --dry-run           Only log install commands, don't execute them
  --interactive, -i   Interactive install, ask before each option
  -y                  Yes to all, don't ask anything
  -a                  Propose/install everything
  -v, --verbose       Verbose mode

Features group selection:
  --default           Don't install default set
  --dev, -d           Install additional dev tools and add dev remotes (chrome, ruff, ..)
  --opt, -o           Install additional optional dependencies (gevent, wkhtml, ebaysdk, ...)
  --docker            Install docker and build a ready to used docker image. Implies --odoo-repo if odoo sources are missing

Individual feature selection:
  --create-config     Clone odoo git repository. Will install git if missing. (enabled by default)
  --odoo-repo         Clone odoo git repository. Will install git if missing. (enabled by default)
  --private-repo, -e  Clone enterprise and upgrade git repository. Will install git if missing. (enabled by default)
  --postgres          Install postgres (enabled by default)
  --minimal-packages  Install packages needed to run odoo core (enabled by default)
  --default-packages  Install default packages needed by some community modules (enabled by default) (implies base-packages)
  --dev-packages      Install dev packages (enabled by dev)
  --dev-remote        Add git dev remotes (enabled by dev)
  --dev-repos         Add documentation and upgrade-utils repos (enabled by dev)
  --chrome, -c        Install chrome latest (enabled by dev)
  --pdf, -w           Install wkhtmltopdf -- qt patched -- (enabled by opt)
  --opt-packages      Install optional packages, for multiworker, and other advanced features (enabled by opt)
  --rtlcss            Install rtlcss (enabled by opt)

Configuration:
  --git-use-http      Use HTTP instead of SSH for git operations
  --branch BRANCH     Branch to checkout after clone
```

## Testing

This command can be tested in a minimal docker image as described in tests/Dockerfile using the command:

`docker build -t odoo-autoinstall -f tests/Dockerfile .`


The docker image can be started in interactive mode using

`docker run -ti --rm -v $(pwd):/home/odoo/autoinstall:ro -v ~/.ssh:/home/odoo/.ssh:ro  -w /home/odoo/autoinstall odoo-autoinstall`

to avoid constant prompt of ssh key

`ssh-add`
`docker run -ti --rm -v $(pwd):/home/odoo/autoinstall:ro -v $SSH_AUTH_SOCK:/tmp/ssh_auth_sock -e SSH_AUTH_SOCK=/tmp/ssh_auth_sock -w /home/odoo/autoinstall odoo-autoinstall`


Note that the scripts requires ssh key linked to a github account in order to clone repositories using ssh and not https

Then, the command to setup the environment is:

`./autoinstall.py`

To have a full dev version, without question (except passwords when needed)

`./autoinstall.py -ay`

