from email._policybase import _PolicyBase


def patch_module():
    def policy_clone(self, **kwargs):
        for arg in kwargs:
            if arg.startswith("_") or "__" in arg:
                raise AttributeError(f"{self.__class__.__name__!r} object has no attribute {arg!r}")
        return orig_policy_clone(self, **kwargs)

    def policy_add(self, other):
        return policy_clone(self, **other.__dict__)

    orig_policy_clone = _PolicyBase.clone
    _PolicyBase.clone = policy_clone
    _PolicyBase.__add__ = policy_add
