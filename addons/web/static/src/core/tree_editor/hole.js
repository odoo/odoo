export class Hole {
    constructor(name) {
        this.name = name;
    }
}

let _holeValues = null;
export function setHoleValues() {
    _holeValues = {};
    return {
        holeValues: _holeValues,
        unset() {
            _holeValues = null;
        },
    };
}

export function upToHole(areEqual) {
    return (v, w) => {
        if (v instanceof Hole) {
            if (_holeValues && v.name in _holeValues) {
                return areEqual(_holeValues[v.name], w);
            }
            _holeValues[v.name] = w;
            return true;
        }
        return areEqual(v, w);
    };
}
