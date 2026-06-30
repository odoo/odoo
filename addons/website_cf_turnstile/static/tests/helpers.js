import { TurnStile } from "@website_cf_turnstile/interactions/turnstile";


/**
 * For unit tests, we want to avoid talking to an external API.
 */
export function patchTurnStile() {
    TurnStile.turnstileURL = "";
}
