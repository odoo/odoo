/**
 * --------------------------------------------------------------------------
 * Bootstrap (v5.1.3): alert.js
 * Licensed under MIT (https://github.com/twbs/bootstrap/blob/main/LICENSE)
 * --------------------------------------------------------------------------
 */

import { defineJQueryPlugin } from './util/index'
import EventHandler from './dom/event-handler'
import BaseComponent from './base-component'
import { enableDismissTrigger } from './util/component-functions'

/**
 * ------------------------------------------------------------------------
 * Constants
 * ------------------------------------------------------------------------
 */

const NAME = 'alert'
const DATA_KEY = 'bs.alert'
const EVENT_KEY = `.${DATA_KEY}`

const EVENT_CLOSE = `close${EVENT_KEY}`
const EVENT_CLOSED = `closed${EVENT_KEY}`
const CLASS_NAME_FADE = 'fade'
const CLASS_NAME_SHOW = 'show'

/**
 * ------------------------------------------------------------------------
 * Class Definition
 * ------------------------------------------------------------------------
 */

class Alert extends BaseComponent {
  // Getters

  static get NAME() {
    return NAME
  }

  // Public

  close() {
    const closeEvent = EventHandler.trigger(this._element, EVENT_CLOSE)

    if (closeEvent.defaultPrevented) {
      return
    }

    this._element.classList.remove(CLASS_NAME_SHOW)

    const isAnimated = this._element.classList.contains(CLASS_NAME_FADE)
    this._queueCallback(() => this._destroyElement(), this._element, isAnimated)
  }

  // Private
  _destroyElement() {
    this._element.remove()
    EventHandler.trigger(this._element, EVENT_CLOSED)
    this.dispose()
  }

  // Static

  static jQueryInterface(config) {
    return this.each(function () {
      const data = Alert.getOrCreateInstance(this)

      if (typeof config !== 'string') {
        return
      }

      if (data[config] === undefined || config.startsWith('_') || config === 'constructor') {
        throw new TypeError(`No method named "${config}"`)
      }

      data[config](this)
    })
  }
}

/**
 * ------------------------------------------------------------------------
 * Data Api implementation
 * ------------------------------------------------------------------------
 */

enableDismissTrigger(Alert, 'close')

/**
 * ------------------------------------------------------------------------
 * jQuery
 * ------------------------------------------------------------------------
 * add .Alert to jQuery only if jQuery is present
 */

defineJQueryPlugin(Alert)

export default Alert
