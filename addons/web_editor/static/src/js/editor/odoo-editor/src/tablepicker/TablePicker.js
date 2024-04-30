/** @odoo-module **/
import { getRangePosition } from '../utils/utils.js';

export class TablePicker extends EventTarget {
    constructor(options = {}) {
        super();
        this.options = options;
        this.options.minRowCount = this.options.minRowCount || 3;
        this.options.minColCount = this.options.minColCount || 3;
        this.options.getContextFromParentRect = this.options.getContextFromParentRect || (() => ({ top: 0, left: 0 }));

        this.rowNumber = this.options.minRowCount;
        this.colNumber = this.options.minColCount;

        this.tablePickerWrapper = document.createElement('div');
        this.tablePickerWrapper.classList.add('oe-tablepicker-wrapper');
        this.tablePickerWrapper.innerHTML = `
            <div class="oe-tablepicker"></div>
            <div class="oe-tablepicker-size"></div>
        `;

        if (this.options.floating) {
            this.tablePickerWrapper.style.position = 'absolute';
            this.tablePickerWrapper.classList.add('oe-floating');
        }

        this.tablePickerElement = this.tablePickerWrapper.querySelector('.oe-tablepicker');
        this.tablePickerSizeViewElement =
            this.tablePickerWrapper.querySelector('.oe-tablepicker-size');

        this.el = this.tablePickerWrapper;

        this.hide();
    }

    render() {
        this.tablePickerElement.innerHTML = '';

        const colCount = Math.max(this.colNumber, this.options.minRowCount);
        const rowCount = Math.max(this.rowNumber, this.options.minRowCount);
        const extraCol = 1;
        const extraRow = 1;

        for (let rowNumber = 1; rowNumber <= rowCount + extraRow; rowNumber++) {
            const rowElement = document.createElement('div');
            rowElement.classList.add('oe-tablepicker-row');
            this.tablePickerElement.appendChild(rowElement);
            for (let colNumber = 1; colNumber <= colCount + extraCol; colNumber++) {
                const cell = this.el.ownerDocument.createElement('div');
                cell.classList.add('oe-tablepicker-cell', 'btn');
                rowElement.appendChild(cell);

                if (rowNumber <= this.rowNumber && colNumber <= this.colNumber) {
                    cell.classList.add('active');
                }

                const bindMouseMove = () => {
                    cell.addEventListener('mouseover', () => {
                        if (this.colNumber !== colNumber || this.rowNumber != rowNumber) {
                            this.colNumber = colNumber;
                            this.rowNumber = rowNumber;
                            this.render();
                        }
                    });
                    this.el.ownerDocument.removeEventListener('mousemove', bindMouseMove);
                };
                this.el.ownerDocument.addEventListener('mousemove', bindMouseMove);
                cell.addEventListener('mousedown', this.selectCell.bind(this));
            }
        }

        this.tablePickerSizeViewElement.textContent = `${this.colNumber}x${this.rowNumber}`;
    }

    show() {
        this.reset();
        this.el.style.display = 'block';
        if (this.options.floating) {
            this._showFloating();
        }
    }

    hide() {
        this.el.style.display = 'none';
    }

    reset() {
        this.rowNumber = this.options.minRowCount;
        this.colNumber = this.options.minColCount;
        this.render();
    }

    selectCell() {
        this.dispatchEvent(
            new CustomEvent('cell-selected', {
                detail: { colNumber: this.colNumber, rowNumber: this.rowNumber },
            }),
        );
    }

    _showFloating() {
        const isRtl = this.options.direction === 'rtl';
        const keydown = e => {
            const actions = {
                ArrowRight: {
                    colNumber: (this.colNumber + (isRtl ? -1 : 1)) || 1,
                    rowNumber: this.rowNumber,
                },
                ArrowLeft: {
                    colNumber: (this.colNumber + (isRtl ? 1 : -1)) || 1,
                    rowNumber: this.rowNumber,
                },
                ArrowUp: {
                    colNumber: this.colNumber,
                    rowNumber: this.rowNumber - 1 || 1,
                },
                ArrowDown: {
                    colNumber: this.colNumber,
                    rowNumber: this.rowNumber + 1,
                },
            };
            const action = actions[e.key];
            if (action) {
                this.rowNumber = action.rowNumber || this.rowNumber;
                this.colNumber = action.colNumber || this.colNumber;
                this.render();

                e.preventDefault();
            } else if (e.key === 'Enter') {
                this.selectCell();
                e.preventDefault();
            } else if (e.key === 'Escape') {
                stop();
                e.preventDefault();
            }
        };

        const offset = getRangePosition(this.el, this.options.document, this.options);
        if (isRtl) {
            this.el.style.right = `${offset.right}px`;
        } else {
            this.el.style.left = `${offset.left}px`;
        }

        this.el.style.top = `${offset.top}px`;

        const stop = () => {
            this.hide();
            this.options.document.removeEventListener('mousedown', stop);
            this.removeEventListener('cell-selected', stop);
            this.options.document.removeEventListener('keydown', keydown, true);
        };

        // Allow the mousedown that activate this command callback to release before adding the listener.
        setTimeout(() => {
            this.options.document.addEventListener('mousedown', stop);
        });
        this.options.document.addEventListener('keydown', keydown, true);
        this.addEventListener('cell-selected', stop);
    }
}
