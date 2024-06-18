import { Component } from '@odoo/owl';

export class FilesList extends Component {
    static template = 'salePdfQuoteBuilder.filesList';
    static props = {
        name: String,
        files: Array,
        id: { type: Number, optional:true }  // Oftentimes received, not used
    };
}
