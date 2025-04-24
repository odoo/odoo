export class Maybe {
    static S(mvs) {
        for (const mv of mvs) {
            if (mv instanceof Just) {
                return mv;
            }
        }
        return Nothing.of();
    }
}

export class Nothing extends Maybe {
    static of() {
        return new Nothing();
    }
    bind(_fn, ..._fns) {
        return Nothing.of();
    }
}

export class Just extends Maybe {
    static of(value) {
        return new Just(value);
    }
    constructor(value) {
        super();
        this.value = value;
    }
    bind(fn, ...fns) {
        if (!fn) {
            return this;
        }
        return fn(this.value).bind(...fns);
    }
}
