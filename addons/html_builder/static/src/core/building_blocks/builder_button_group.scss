.o-hb-button-group.btn-group {
    --BtnGroup__btn-spacing: calc(var(--border-width) * -1);

    flex: 1 1 50%;
    min-width: 0;
    align-items: center;

    .o-hb-btn {
        flex: 1 1 auto;
        align-self: stretch;

        &.active {
            z-index: 2;
        }
    }

    // Bootstrap rounds the last child, so restore the radius on the last visible
    // one to avoid a squarish right edge in case of a hidden button at the end.
    .o-hb-btn:not(.d-none):has(+ .o-hb-btn.d-none):not(:has(~ .o-hb-btn:not(.d-none))) {
        @include border-end-radius(var(--btn-border-radius));
    }
}
