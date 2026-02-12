// The WebSerial types are not included by default in TypeScript
// because they are only supported by one major browser (Chromium),
// so we define the types manually here.
//
// See: https://github.com/saschanaz/types-web?tab=readme-ov-file#why-is-my-fancy-api-still-not-available-here

type SerialPortOptions = {
    baudRate: number;
    bufferSize?: number;
    dataBits?: 7 | 8;
    flowControl?: "none" | "hardware";
    parity?: "none" | "even" | "odd";
    stopBits?: 1 | 2;
};

type SerialPortInfo =
    | {
          usbVendorId: number;
          usbProductId: number;
          bluetoothServiceClassId: undefined;
      }
    | {
          usbVendorId: undefined;
          usbProductId: undefined;
          bluetoothServiceClassId: number | string;
      };

type SerialPortGetSignals = {
    clearToSend: boolean;
    dataCarrierDetect: boolean;
    dataSetReady: boolean;
    ringIndicator: boolean;
};

type SerialPortSetSignals = {
    dataTerminalReady?: boolean;
    requestToSend?: boolean;
    break?: boolean;
};

type SerialPortFilter = {
    bluetoothServiceClassId?: number | string;
    usbVendorId?: number;
    usbProductId?: number;
};

type RequestPortOptions = {
    filters?: SerialPortFilter[];
    allowedBluetoothServiceClassIds?: Array<number | string>;
};

interface SerialPort {
    connected: boolean;
    readable: ReadableStream<Uint8Array>;
    writable: WritableStream<Uint8Array>;

    close: () => Promise<void>;
    forget: () => Promise<void>;
    getInfo: () => SerialPortInfo;
    getSignals: () => Promise<SerialPortGetSignals>;
    setSignals: (options?: SerialPortSetSignals) => Promise<void>;
    open: (options: SerialPortOptions) => Promise<void>;
}

interface Serial {
    getPorts: () => Promise<SerialPort[]>;
    requestPort: (options?: RequestPortOptions) => Promise<SerialPort>;
}

interface Navigator {
    serial?: Serial;
}
