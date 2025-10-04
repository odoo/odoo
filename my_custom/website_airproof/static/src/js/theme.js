// /** @odoo-module **/

// import { Component } from "@odoo/owl";
// import { loadJS } from "@web/core/assets";

// export class ScrollToTop extends Component {
//     setup() {
//         window.addEventListener("scroll", () => {
//             const btn = document.getElementById("scrollToTop");
//             btn.style.display = window.scrollY > 200 ? "block" : "none";
//         });
//     }

//     scroll() {
//         window.scrollTo({ top: 0, behavior: "smooth" });
//     }
// }

// Mount component và gán vào odoo global
// odoo.__scrollComponent__ = new ScrollToTop();

// <template id="scroll_button" name="Scroll Button" inherit_id="website.layout">
//     <xpath expr="//body" position="inside">
//         <button id="scrollToTop" t-attf-onclick="odoo.__scrollComponent__.scroll()" style="display: none;">
//             ⬆ Top
//         </button>
//     </xpath>
// </template>
