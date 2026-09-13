from odoo.orm.runtime._registry_signaling import _RegistrySignalingMixin


class _Signaling(_RegistrySignalingMixin):
    def __init__(self) -> None:
        self._init_signaling_state()


def test_a_clean_registry_names_no_model():
    reg = _Signaling()
    assert reg.registry_invalidated is False
    assert reg.invalidated_model_names == set()


def test_named_setups_accumulate_their_models():
    reg = _Signaling()
    reg._note_invalidated_models(["res.partner"])
    reg._note_invalidated_models(["res.users", "res.partner"])
    assert reg.registry_invalidated is True
    assert reg.invalidated_model_names == {"res.partner", "res.users"}


def test_a_full_setup_widens_the_scope_to_the_whole_registry():
    reg = _Signaling()
    reg._note_invalidated_models(["res.partner"])
    reg._note_invalidated_models(None)
    assert reg.invalidated_model_names is None
    reg._note_invalidated_models(["res.users"])
    assert reg.invalidated_model_names is None


def test_flipping_the_flag_by_hand_has_no_named_scope():
    reg = _Signaling()
    reg._note_invalidated_models(["res.partner"])
    reg.registry_invalidated = True
    assert reg.invalidated_model_names is None
    reg._note_invalidated_models(["res.partner"])
    assert reg.invalidated_model_names is None


def test_clearing_the_flag_forgets_the_scope():
    reg = _Signaling()
    reg._note_invalidated_models(["res.partner"])
    reg.registry_invalidated = False
    assert reg.invalidated_model_names == set()
    reg._note_invalidated_models(["res.users"])
    assert reg.invalidated_model_names == {"res.users"}


def test_an_empty_named_setup_keeps_a_named_scope():
    reg = _Signaling()
    reg._note_invalidated_models([])
    assert reg.registry_invalidated is True
    assert reg.invalidated_model_names == set()
