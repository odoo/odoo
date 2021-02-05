# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).


def post_load():
    # make import in post_load to avoid applying monkey patches when this
    # module is not installed
    from . import models
    from . import controllers
