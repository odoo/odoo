import requests
import json

orig_request_json = requests.Response.json

# The requests library uses different libraries to parse json objects depending on
# whether or not the simplejson library is installed
# (https://github.com/psf/requests/blob/dc9dbdfb3434c6e58d48fd102f93e5342308817e/src/requests/compat.py#L74).
# This in turn causes our try/excepts to fail if the simplejson library is installed in the env
# we simply re-raise the json error in case the simplejson library is installed so our try/excepts flows
# are not broken by the existence of a random package
# This is only valid for python versions < 3.10 that install requests==2.25.  This issue
# was fixed in requests==2.27


def patch_module():
    try:
        import simplejson  # noqa: PLC0415
    except ImportError:
        return    # no need to change anything if simplejson isn't installed
    else:
        def new_json(self, **kwargs):
            try:
                return orig_request_json(self, **kwargs)
            except simplejson.JSONDecodeError as e:
                raise json.JSONDecodeError(e.msg, e.doc, e.pos)
        requests.Response.json = new_json
