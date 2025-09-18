// @ts-check

/** @module @web/boot/main - Entry point that launches the web client (replaced in enterprise) */

import { startWebClient } from "@web/boot/start";
import { WebClient } from "@web/webclient/webclient";
/**
 * This file starts the webclient. It is in its own file to allow its replacement
 * in enterprise. The enterprise version of the file uses its own webclient import,
 * which is a subclass of the above Webclient.
 */

startWebClient(/** @type {any} */ (WebClient));
