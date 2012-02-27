var py = require('../lib/py.js'),
    expect = require('expect.js');

expect.Assertion.prototype.tokens = function (n) {
    var length = this.obj.length;
    this.assert(length === n + 1,
                'expected ' + this.obj + ' to have ' + n + ' tokens',
                'expected ' + this.obj + ' to not have ' + n + ' tokens');
    this.assert(this.obj[length-1].id === '(end)',
                'expected ' + this.obj + ' to have and end token',
                'expected ' + this.obj + ' to not have an end token');
};

expect.Assertion.prototype.constant = function (value) {
    this.assert(this.obj.id === '(constant)',
                'expected ' + this.obj + ' to be a constant token',
                'expected ' + this.obj + ' not to be a constant token');
    this.assert(this.obj.value === value,
                'expected ' + this.obj + ' to have tokenized ' + value,
                'expected ' + this.obj + ' not to have tokenized ' + value);
};
expect.Assertion.prototype.number = function (value) {
    this.assert(this.obj.id === '(number)',
                'expected ' + this.obj + ' to be a number token',
                'expected ' + this.obj + ' not to be a number token');
    this.assert(this.obj.value === value,
                'expected ' + this.obj + ' to have tokenized ' + value,
                'expected ' + this.obj + ' not to have tokenized ' + value);
};
expect.Assertion.prototype.string = function (value) {
    this.assert(this.obj.id === '(string)',
                'expected ' + this.obj + ' to be a string token',
                'expected ' + this.obj + ' not to be a string token');
    this.assert(this.obj.value === value,
                'expected ' + this.obj + ' to have tokenized ' + value,
                'expected ' + this.obj + ' not to have tokenized ' + value);
};

describe('Tokenizer', function () {
    describe('simple literals', function () {
        it('tokenizes numbers', function () {
            var toks = py.tokenize('1');
            expect(toks).to.have.tokens(1);
            expect(toks[0]).to.be.number(1);

            var toks = py.tokenize('-1');
            expect(toks).to.have.tokens(2);
            expect(toks[0].id).to.be('-');
            expect(toks[1]).to.be.number(1);

            var toks = py.tokenize('1.2');
            expect(toks).to.have.tokens(1);
            expect(toks[0]).to.be.number(1.2);

            var toks = py.tokenize('.42');
            expect(toks).to.have.tokens(1);
            expect(toks[0]).to.be.number(0.42);
        });
        it('tokenizes strings', function () {
            var toks = py.tokenize('"foo"');
            expect(toks).to.have.tokens(1);
            expect(toks[0]).to.be.string('foo');

            var toks = py.tokenize("'foo'");
            expect(toks).to.have.tokens(1);
            expect(toks[0]).to.be.string('foo');
        });
        it('tokenizes bare names', function () {
            var toks = py.tokenize('foo');
            expect(toks).to.have.tokens(1);
            expect(toks[0].id).to.be('(name)');
            expect(toks[0].value).to.be('foo');
        });
        it('tokenizes constants', function () {
            var toks = py.tokenize('None');
            expect(toks).to.have.tokens(1);
            expect(toks[0]).to.be.constant('None');

            var toks = py.tokenize('True');
            expect(toks).to.have.tokens(1);
            expect(toks[0]).to.be.constant('True');

            var toks = py.tokenize('False');
            expect(toks).to.have.tokens(1);
            expect(toks[0]).to.be.constant('False');
        });
    });
    describe('collections', function () {
        it('tokenizes opening and closing symbols', function () {
            var toks = py.tokenize('()');
            expect(toks).to.have.tokens(2);
            expect(toks[0].id).to.be('(');
            expect(toks[1].id).to.be(')');
        });
    });
});