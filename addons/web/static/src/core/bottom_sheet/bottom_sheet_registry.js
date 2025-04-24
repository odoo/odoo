import { registry } from "@web/core/registry";

/**
 * Registry for mapping components to their bottom sheet alternatives
 *
 * Registry entries can include:
 * - Component: The component to use as mobile alternative
 * - slots: Object mapping source content to bottom sheet slots
 * - options: Additional configuration options for the bottom sheet
 *
 * Example usage:
 *
 * // When defining a component
 * export class MyDesktopComponent extends Component { ... }
 *
 * // Register its mobile alternative
 * registry.category("bottom_sheet_components").add(
 *   "MyDesktopComponent",
 *   {
 *     Component: MyMobileComponent,
 *     slots: {
 *       // Map content to specific slots in BottomSheet
 *       content: "default",  // Map the main content to default slot
 *       header: "header",    // Map any header content to header slot
 *       footer: "footer"     // Map footer content to footer slot
 *     },
 *     options: {
 *       // Additional BottomSheet options
 *       initialHeightPercent: 60
 *     }
 *   }
 * );
 */
registry.category("bottom_sheet_components");
