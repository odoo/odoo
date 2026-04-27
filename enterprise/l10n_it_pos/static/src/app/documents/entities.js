export class Heading extends String {
    static index = 1;
    constructor(text, font = 1) {
        super(text);
        this.text = text;
        this.font = font;
        this.index = Heading.index++;
    }

    static resetIndex() {
        Heading.index = 1;
    }
}
