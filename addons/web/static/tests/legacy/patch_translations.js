/** @odoo-module alias=@web/../tests/patch_translations default=false */

import { translatedTerms, translationLoaded } from "@web/core/l10n/translation";

translatedTerms[translationLoaded] = true;
