import { rpc } from "@web/core/network/rpc";

function makeGooglePlacesSession() {
    let current;

    /**
     * Used to generate a unique session ID for the places API.
     * According to the API docs:
     * "The session begins when the user starts typing a query,
     * and concludes when they select a place and a call to Place Details is made.
     * Each session can have multiple queries, followed by one place selection.
     * [...] Once a session has concluded, the token is no longer valid;
     * your app must generate a fresh token for each session."
     * https://developers.google.com/maps/documentation/places/web-service/details#session_tokens
     */
    function generateUUID() {
        return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
            const r = (Math.random() * 16) | 0,
                v = c == "x" ? r : (r & 0x3) | 0x8;
            return v.toString(16);
        });
    }

    function getAddressPropositions(params = {}) {
        if (!params.session_id) {
            current = current || generateUUID();
            params.session_id = current;
        }
        return rpc("/autocomplete/address", params);
    }

    async function getAddressDetails(params = {}) {
        if (!params.session_id) {
            current = current || generateUUID();
            params.session_id = current;
        }
        current = null;
        return rpc("/autocomplete/address_full", params);
    }

    return {
        get sessionToken() {
            return current;
        },
        getAddressPropositions,
        getAddressDetails,
    };
}

export const googlePlacesSession = makeGooglePlacesSession();
