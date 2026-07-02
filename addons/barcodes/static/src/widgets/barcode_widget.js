import { registry } from "@web/core/registry";
import { CharField, charField } from "@web/views/fields/char/char_field";
import { scanBarcode } from "@web/core/barcode/barcode_dialog";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class BarcodeWidget extends CharField {
    static template = "barcodes.BarcodeField";
    static props = {
        ...standardFieldProps,
        barcodeDisplay: { type: String, optional: true },
        barcodeType: { type: String, optional: true },
        width: { type: Number, optional: true },
        height: { type: Number, optional: true },
        humanReadable: { type: Boolean, optional: true },
        quiet: { type: Boolean, optional: true },
        mask: { type: String, optional: true },
        barLevel: { type: String, optional: true },
        enableZoom: { type: Boolean, optional: true },
    };
    static defaultProps = {
        barcodeType: "QR",
        barcodeDisplay: "text_image",
        width: 90
    };

    setup() {
        super.setup();
    }

    get value() {
        return this.props.record.data[this.props.name]
    }

    get string() {
        return this.props.record.data[this.props.name]
    }

    get icon_class() {
        return this.is_square ? 'fa fa-qrcode' : 'fa fa-barcode'
    }

    get barcode_src() {
        const { barcodeType, width, height, humanReadable, quiet, mask, barLevel } = this.props;

        const params = new URLSearchParams();

        if (barcodeType) params.set('barcode_type', barcodeType);
        if (this.value) params.set('value', this.value);
        params.set('humanreadable', humanReadable ? 1 : 0);
        params.set('quiet', quiet ? 1 : 0);
        if (mask) params.set('mask', mask);
        if (barLevel) params.set('barLevel', barLevel);

        if (this.is_square) {
            const size = Math.max(width || 0, height || 0)
            if (size) {
                params.set('width', size);
                params.set('height', size);
            }
        } else {
            if (width) params.set('width', width);
            if (height) params.set('height', height);
        }

        return `/report/barcode?${params.toString()}`;
    }

    get hasZoom() {
        return this.props.enableZoom && this.value;
    }
    get zoomAttributes() {
        return {
            template: "web.ImageZoomTooltip",
            info: JSON.stringify({ url: this.barcode_src }),
        };
    }

    get is_square() {
        return ['QR'].includes(this.props.barcodeType) || (this.props.width && this.props.height && this.props.width === this.props.height)
    }

    async onBarcodeBtnClick() {
        const barcode = await scanBarcode(this.env);
        if (barcode) await this.props.record.update({barcode: barcode});
    }
}

export const barcodeWidget = {
    ...charField,
    component: BarcodeWidget,
    supportedOptions: [
        {
            label: "Display",
            name: "barcode_display",
            type: "selection",
            default: 'text_image',
            choices: [
                { label: "Text & Image", value: "text_image"},
                { label: "Text", value: "text"},
                { label: "Image", value: "image"},
            ]
        },
        {
            label: "Type",
            name: "barcode_type",
            type: "selection",
            default: 'QR',
            choices: [
                { label: "Codabar", value: "Codabar"},
                { label: "Code11", value: "Code11"},
                { label: "Code128", value: "Code128"},
                { label: "EAN13", value: "EAN13"},
                { label: "EAN8", value: "EAN8"},
                { label: "Extended39", value: "Extended39"},
                { label: "Extended93", value: "Extended93"},
                { label: "FIM", value: "FIM"},
                { label: "I2of5", value: "I2of5"},
                { label: "MSI", value: "MSI"},
                { label: "POSTNET", value: "POSTNET"},
                { label: "QR", value: "QR"},
                { label: "Standard39", value: "Standard39"},
                { label: "Standard93", value: "Standard93"},
                { label: "UPCA", value: "UPCA"},
                { label: "USPS_4State", value: "USPS_4State"},
            ]
        },
        {
            label: "Width",
            name: "width",
            type: "number",
        },
        {
            label: "Height",
            name: "height",
            type: "number",
        },
        {
            label: "Human Readable",
            name: "humanreadable",
            type: "boolean",
        },
        {
            label: "Quiet",
            name: "quiet",
            type: "boolean",
        },
        {
            label: "Mask",
            name: "mask",
            type: "string",
        },
        {
            label: "QR Code Correction Level",
            name: "barlevel",
            type: "selection",
            default: 'L',
            choices: [
                { label: "High", value: "H"},
                { label: "Quartile", value: "Q"},
                { label: "Medium", value: "M"},
                { label: "Low", value: "L"},
            ]
        },
        {
            label: "Enable zoom",
            name: "zoom",
            type: "boolean",
        },

    ],
    extractProps: ({ attrs, options }) => ({
        barcodeDisplay: options.barcode_display,
        barcodeType: options.barcode_type,
        width: options.width || attrs.width,
        height: options.height || attrs.height,
        humanReadable: options.humanreadable,
        quiet: options.quiet,
        mask: options.mask,
        barLevel: ['H', 'L', 'M', 'Q'].includes(options.barlevel) ? options.barlevel : undefined,
        enableZoom: options.zoom,
    }),
};

registry.category("fields").add("barcode", barcodeWidget);
