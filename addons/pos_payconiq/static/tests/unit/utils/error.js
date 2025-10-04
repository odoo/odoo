export class ErrorWithObjectBody extends Error {
    constructor(message, data) {
        super(message);
        this.data = data;
    }
}
