import { Just, Maybe, Nothing } from "@web/core/tree_editor/maybe_monad";

function* lazyValues(fns, v) {
    for (const fn of fns) {
        yield fn(v);
    }
}

export class Pattern {
    static C(patterns) {
        return _Pattern.of(
            (r) => Just.of(r).bind(...patterns.map((p) => p.detect.bind(p))),
            (r) => Just.of(r).bind(...patterns.map((p) => p.make.bind(p)).reverse())
        );
    }
    static S(patterns) {
        return _Pattern.of(
            (r) =>
                Maybe.S(
                    lazyValues(
                        patterns.map((p) => p.detect.bind(p)),
                        r
                    )
                ),
            (r) =>
                Maybe.S(
                    lazyValues(
                        patterns.map((p) => p.make.bind(p)),
                        r
                    )
                )
        );
    }
    /**
     * @param {any} _o
     * @returns {Just|Nothing}
     */
    detect(_o) {
        return Nothing.of();
    }
    make(_v) {
        return Nothing.of();
    }
}

export class _Pattern extends Pattern {
    static of(detect, make) {
        return new _Pattern(detect, make);
    }
    constructor(detect, make) {
        super();
        this._detect = detect;
        this._make = make;
    }
    detect(o) {
        return this._detect(o);
    }
    make(v) {
        return this._make(v);
    }
}
