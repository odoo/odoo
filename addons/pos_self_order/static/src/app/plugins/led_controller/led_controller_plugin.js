import { Plugin, useConfig, t } from "@odoo/owl";
import { BoxaPosStrategy } from "./boxapos_strategy";
import { hexToRgb, SUCCESS_COLOR, ERROR_COLOR, ODOO_COLOR, ANIMATION_DURATION_MS } from "./utils";

const SUPPORTED_STRATEGIES = [BoxaPosStrategy];

export class DefaultStrategy {
    async setSuccessState(...args) {}
    async setErrorState(...args) {}
    async setIdleState(...args) {}
    async onStartup(...args) {}
}

export class LedControllerPlugin extends Plugin {
    static id = "led_controller";

    setup() {
        this.idleColor = hexToRgb(useConfig("idleColor", t.string().optional(""))) || ODOO_COLOR;
        this.strategy = new DefaultStrategy();

        this.lockTimer = null;
        this.isLocked = false;
        this.pendingColor = null;

        this.detectController();
    }

    /**
     * Iterates over supported strategies to find and configure a valid controller.
     */
    async detectController() {
        for (const StrategyClass of SUPPORTED_STRATEGIES) {
            const instance = await StrategyClass.detect();
            if (instance) {
                this.strategy = instance;
                break;
            }
        }

        const started = await this.strategy.onStartup();
        if (started === false) {
            this.strategy = new DefaultStrategy();
            return;
        }
        this.setIdleState();
    }

    /**
     * Plays a visual animation and locks the controller state until it finishes.
     *
     * @param {Function} action - The async action to execute.
     * @param {string} [fallbackColor=this.idleColor] - The fallback color after the animation.
     * @param {number} [duration=ANIMATION_DURATION_MS] - How long to lock the controller.
     */
    async playAnimation(action, fallbackColor = this.idleColor, duration = ANIMATION_DURATION_MS) {
        this.isLocked = true;
        this.pendingColor = fallbackColor;

        if (this.lockTimer) {
            clearTimeout(this.lockTimer);
        }

        try {
            const success = await action();
            if (success === false) {
                this.strategy = new DefaultStrategy();
            }
        } catch (error) {
            error;
            this.strategy = new DefaultStrategy();
        } finally {
            this.lockTimer = setTimeout(() => {
                this.isLocked = false;
                const colorToApply = this.pendingColor;
                this.pendingColor = null;
                this.setIdleState(colorToApply);
            }, duration);
        }
    }

    /**
     * Plays the success animation.
     */
    async setSuccessState() {
        return this.playAnimation(() => this.strategy.setSuccessState(), SUCCESS_COLOR);
    }

    /**
     * Plays the error animation.
     */
    async setErrorState() {
        return this.playAnimation(() => this.strategy.setErrorState(), ERROR_COLOR);
    }

    /**
     * Sets the controller back to the idle state color, unless an animation is currently locked.
     *
     * @param {string} [color=this.idleColor] - The idle color to set.
     */
    async setIdleState(color = this.idleColor) {
        if (this.isLocked) {
            this.pendingColor = color;
            return;
        }

        this.pendingColor = null;
        const success = await this.strategy.setIdleState(color);
        if (success === false) {
            this.strategy = new DefaultStrategy();
        }
    }
}
