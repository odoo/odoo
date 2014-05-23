#/bin/sh
set -e

ODOO=https://github.com/odoo/odoo.git
DEV=https://github.com/odoo-dev/odoo.git

usage () {
cat <<EOF
Usage: $0 [-m] [COPYNAME]

Checks out and sets up the Odoo git repository for "internal" development.

* Checks out the "production" repository (production branches) as the "odoo"
  remote
* Checks out the "development" repository (for employee development branches)
  as the "dev" repository

By default, the working copy is "odoo"

Options:
-h        displays this help text
-m        includes github's merge refs. These are the pull requests to "odoo"
          which merge cleanly into the main repository, after having applied
          them to said repository
EOF
}

while getopts :hm opt
do
    case $opt in
        h)
            usage
            exit 0
            ;;
        m)
            include_merge=yes
            ;;
        *)
            usage
            exit 1
            ;;
    esac
done

shift $((OPTIND-1))
copyname=${1:-"odoo"}

# Collect basic configuration data, ensures correct configuration of that repo
printf "Enter your full name: "
read name
printf "Enter your (work) email: "
read email

# create & set up repo
git init $copyname
cd $copyname

git config user.name "$name"
git config user.email "$email"

# pre-push script preventing push to odoo repo by default. Git just execs
# them, so they need a correct shebang and exec bit
# if things get more extensive, should probably use git init templates
cat <<EOF > .git/hooks/pre-push
#!/bin/sh
remote="\$1"
url="\$2"

if [ "\$url" != "$ODOO" ]
then
    exit 0
fi

echo "Pushing to the odoo remote ($ODOO) is forbidden, push to the dev remote"
echo
echo "See git help push if you really want to push to odoo"
exit 1

EOF
chmod +x .git/hooks/pre-push

# add basic repos as remotes
git remote add odoo $ODOO
git remote add dev $DEV

if [ $include_merge ]
then
    git remote add merge $ODOO
    git config remote.merge.fetch '+refs/pull/*/merge:refs/remotes/merge/*'
fi

echo
git remote update

exit 0
