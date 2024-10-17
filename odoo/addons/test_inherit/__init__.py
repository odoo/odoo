# -*- coding: utf-8 -*-
from .models import *  # noqa: F403

from .models.mother_inherit_1 import Test_Mother_Underscore
from .models.mother_inherit_4 import TestInheritMother
from .models.test_models import (
    ResPartner, Test_Inherit_Child, Test_Inherit_Daughter,
    Test_Inherit_Mixin, Test_Inherit_Parent, Test_Inherit_Property, Test_New_ApiMessage,
    Test_New_ApiSelection,
)
