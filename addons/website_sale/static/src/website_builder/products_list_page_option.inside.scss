// Note: many lines in this file are disabled because variables such as
// $o-we-handles-accent-color are not accessible from this bundle. The final
// effect is that the colored outline around previews is not visible.
// (TODO: make the variables accessible again?)

// ==================
// Edit-Mode Previews
// ==================

// body.editor_enable {
//   // Outline the category description box
//   #category_header {
//     &:has(br:first-child:last-child), &:empty {
//       outline: $border-width dashed fade-currentColor(25%);

//       &:hover {
//         outline: $border-width * 2 solid $o-we-handles-accent-color;
//       }
//     }
//   }

//   // Outline product description boxes
//   .oe_subdescription {
//     div:has(br:first-child:last-child):not(:hover), div:empty:not(:hover) {
//       outline: $border-width dashed fade-currentColor(25%);
//     }
//   }
// }


// ==========================
// Preview Components (/shop)
// ==========================
body.editor_enable:has(.o_wsale_edit_preview_enabled) {
  // Hide default handles when other elements are highlighted
  // Note: Since the handles have been moved outside the iframe,
  // these selectors don't work anymore.
  // TODO: Find a solution to make this work again.
  // &:has(.o_wsale_previewing_sidebar),
  // &:has(.o_wsale_previewing_filmstrip),
  // &:has(.o_wsale_previewing_offcanvas),
  // &:has(.o_wsale_previewing_description),
  // &:has(.o_wsale_previewing_floating_bar) {
  //   .o_handles {
  //     visibility: hidden;
  //   }
  // }

  // @mixin _showcase {
  //   z-index: $zindex-tooltip;
  //   outline: $border-width * 2 solid $o-we-handles-accent-color;
  // }

  // Sidebar
  @keyframes sidebar_preview {
      to {
        min-width: o-to-rem(240px);
        max-width: var(--o-wsale-sidebar-maxwidth, 15rem);
        opacity: 1;
        transform: translateX(0);
      }
  }

  .o_wsale_sidebar_preview {
    padding: 0;
    flex: 0 0 25%;
    min-width: 0;
    max-width: 0;
    transform: translateX(-50%);
    opacity: 0;
  }

  .o_wsale_previewing_sidebar {
    // #products_grid_before {
    //   @include _showcase();
    // }

    .o_wsale_sidebar_preview:first-child {
      @include media-breakpoint-up(lg) {
        animation: sidebar_preview .2s forwards;
        // @include _showcase();
      }
    }
  }

  // Categories Filmstrip (top)
  @keyframes filmstrip_preview {
      to {
        max-height: 100px;
        transform: translateY(0);
        opacity: 1;
      }
  }

  .o_wsale_filmstrip_preview {
    max-height: 0;
    padding: 0;
    transform: translateY(-50%);
    opacity: 0;
  }

  .o_wsale_previewing_filmstrip {
    // .o_wsale_filmstip_container {
    //   @include _showcase();
    // }

    .o_wsale_filmstrip_preview {
      animation: filmstrip_preview .4s forwards;
      // @include _showcase();
      // outline-offset: 2px;
    }
  }

  // Offcanvas
  .o_wsale_previewing_offcanvas {
    #o_wsale_offcanvas {
      visibility: visible;
      transform: none;
      box-shadow: $box-shadow-lg;
      // @include _showcase();
    }
  }

  // This prevents a glitch animation when we stop hovering over the 'Filter / Offcanvas' option
  .o_wsale_edit_preview_enabled:not(.o_wsale_previewing_offcanvas) {
      #o_wsale_offcanvas #o_wsale_price_range_option_inner * {
        visibility: hidden !important;
      }
  }

  // Descriptions
  .o_wsale_description_preview {
    opacity: 0;
    transition: all .2s;

    .placeholder {
      transform: translateY(-50%);
      min-height: 0em;
      transition: all .2s;
      opacity: .15;
    }
  }

  .o_wsale_previewing_description {
    // .oe_product_cart .oe_subdescription {
    //   @include _showcase();
    // }

    .o_wsale_description_preview {
      opacity: 1;
      // outline: $border-width solid $o-we-handles-accent-color;
      // outline-offset: 2px;

      .placeholder {
        transform: translateY(0);
        min-height: .4em;
      }
    }
  }

  // Floating Bar
  @keyframes floating_bar_preview {
      to {
        transform: translateY(0);
        opacity: 1;
      }
  }
  .o_wsale_floating_bar_preview {
    transform: translateY(100%);
    opacity: 0;
    transition: all .2s;
  }

  .products_header {
    max-height: 100px;
    overflow: hidden;
    transition: all .2s;
  }

  .o_wsale_previewing_floating_bar {
    // #o_wsale_floating_bar {
    //   @include _showcase();
    // }

    .products_header {
      max-height: 0px;
    }

    .o_wsale_floating_bar_preview {
      // @include _showcase();
      animation: floating_bar_preview .2s forwards;
    }
  }
}
