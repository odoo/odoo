# Requirements version policy

Odoo relies on debian/ubuntu package to ensure a good compatibility between packages as well as the benefits from the security backports.
On debian base system is is adviced to install debian packages instead of relying on pip and virtual environements. 

The provides requirements can be used on non debian system, or for testing, but using them for production is not adviced.

The pinned versions are either based on debian, matching the python version to the corresponding debian/ubuntu lts, or on specific security patches for critical packages. 


# Installing debian packages
The script debinstall.sh can be used to install the requirements using de debian packages only.


# Using a venv
Even when using a venv , it is adviced to use --system-site-packages in order to use the base debian packages if present. In this case, a version of the requirements without the security pinned version can be used, in order to use the package provided by debian, with security patches.

