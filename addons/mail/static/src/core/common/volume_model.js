import { Record } from "./record";

export class Volume extends Record {
    static id = "persona";

    persona = Record.one("Persona");
    volume = 1;
}

Volume.register();
