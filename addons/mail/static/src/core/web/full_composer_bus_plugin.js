import { EventBus, Plugin, t, useConfig } from "@odoo/owl";

/**
 * Bus between a composer and the full composer it opened, e.g. to retrieve
 * the editor content when the full composer is closed by accident.
 *
 * Config:
 * - `bus`: the EventBus given by the composer opening the full composer.
 */
export class FullComposerBusPlugin extends Plugin {
    bus = useConfig("bus", t.instanceOf(EventBus));
}
