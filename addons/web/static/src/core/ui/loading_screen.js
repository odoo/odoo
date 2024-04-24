/** The loading screen is instanciate by the block ui and the offline page */

// sprites

class Sprite {
    static width = 31;
    static height = 13;

    constructor(width, height) {
        this.state = {
            width: width || this.constructor.width,
            height: height || this.constructor.height,
        };
    }

    render() {
        if (!this.el) {
            this.el = this.createNode();
        }
        this.el.setAttribute("transform", `translate(${(-this.state.width/2)} ${(-this.state.height/2)}) scale(${(this.state.width/this.constructor.width)} ${(this.state.height/this.constructor.height)})`);
        return this.el;
    }

    createNode() {
        const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
        text.setAttribute('style', "font-weight: bold; font-size: 12px;");
        text.setAttribute('fill', "#724b68");
        text.textContent = "Odoo";
        return text;
    }

    destroy() {
        if (this.el) {
            this.el.remove()
        }
    }
}
class SpriteBox extends Sprite {
    static width = 67;
    static height = 70;

    createNode() {
        const image = document.createElementNS("http://www.w3.org/2000/svg", "image");
        image.setAttribute("href", "/web/static/src/core/ui/box.svg");
        return image;
    }
}
class SpritePerson extends Sprite {
    static width = 34;
    static height = 60;

    constructor(width, height, frame) {
        super(width, height);
        this.state.frame = frame || "down";
        this.data = {
            down: [[150, 36, 58, 40, 0, 0, 0], [150, 36, 58, 80, 0, 0, 2], [150, 36, 58, 120, 0, 0, 0], [150, 36, 58, 0, 0, 0, 2]],
            downStop: [[150, 36, 58, 0, 0, 0, 2]],
            left: [[150, 36, 60, 0, 60, 0, 0], [150, 36, 60, 40, 60, 0, 0], [150, 36, 60, 80, 60, 0, 0], [150, 36, 60, 120, 60, 0, 0]],
            leftStop: [[150, 36, 60, 0, 60, 0, 0]],
            right: [[150, 36, 60, 2, 120, 0, 0], [150, 36, 60, 40, 120, 0, 0], [150, 36, 60, 80, 120, 0, 0], [150, 36, 60, 120, 120, 0, 0]],
            rightStop: [[150, 36, 60, 40, 120, 0, 0]],
            up: [[150, 36, 60, 40, 180, 0, 0], [150, 36, 60, 80, 180, 0, 2], [150, 36, 60, 120, 180, 0, 0], [150, 36, 60, 0, 180, 0, 2]],
            upStop: [[150, 36, 60, 0, 180, 0, 2]],
        };
        this.colorize();
    }

    colorize() {
        this.color = {
            jacket: ["#724b68", "#6e7077"][Math.floor(Math.random() * 2)],
            shirt: ["#724b68", "#ffffff", "#7eb8ff"][Math.floor(Math.random() * 3)],
            hair: ["#000000", "#4b2f1e"][Math.floor(Math.random() * 2)],
            pants: ["#000066", "#000000", "#575757"][Math.floor(Math.random() * 3)],
            skin: ["#e9c1ad", "#8f6e5e", "#ddc095"][Math.floor(Math.random() * 3)],
            shoes: ["#ffffff", "#000000", "#97694c"][Math.floor(Math.random() * 3)],
        };
        if (this.el) {
            const shapes = this.el.querySelectorAll('g[clip-path] g rect');
            shapes[0].setAttribute('fill', this.color.shirt);
            shapes[1].setAttribute('fill', this.color.shoes);
            shapes[2].setAttribute('fill', this.color.pants);
            shapes[3].setAttribute('fill', this.color.jacket);
            shapes[4].setAttribute('fill', this.color.skin);
            shapes[5].setAttribute('fill', this.color.hair);
        }
    }

    render() {
        super.render();

        const frames = this.data[this.state.frame] || Object.values(this.data)[0];
        const time = new Date().getTime();
        if (!this.frameTime || this.currentFrame !== this.state.frame) {
            this.frameTime = time;
            this.currentFrame = this.state.frame;
            this.totalTime = frames.map(f => f[0]).reduce((a,b) => a + b);
        }
        let frameTime = (time - this.frameTime) % this.totalTime;
        let no = 0;
        while(frames[no][0] && frameTime > frames[no][0]) {
            frameTime -= frames[no][0];
            no++;
        }
        const dataFrame = frames[no % frames.length] || frames[0];

        const clip = this.el.querySelector("clipPath");
        clip.firstElementChild.setAttribute("width",dataFrame[1]);
        clip.firstElementChild.setAttribute("height",   dataFrame[2]);
        const clipped = clip.nextElementSibling;
        clipped.querySelector("g").setAttribute("width",dataFrame[1]);
        clipped.querySelector("g").setAttribute("height",   dataFrame[2]);
        clipped.querySelector("g").setAttribute("transform", `translate(${dataFrame[5]} ${dataFrame[6]})`);
        clipped.querySelector("g g").setAttribute("transform", `translate(${-dataFrame[3]} ${-dataFrame[4]})`);

        return this.el;
    }

    createNode() {
        if (!SpritePerson.uniqId) {
            SpritePerson.uniqId = 1;
        }
        this._id = SpritePerson.uniqId++;
        const node = document.createElementNS("http://www.w3.org/2000/svg", "g");
        node.innerHTML = `
            <clipPath id="LoadingScreenSpritePersonClip-${this._id}"><rect x="0" y="0"/></clipPath>
            <g clip-path="url(#LoadingScreenSpritePersonClip-${this._id})">
                <g transform="translate(0 0)">
                    <use href="/web/static/src/core/ui/person.svg#shirt"/>
                    <clipPath id="person_shirt_clip-${this._id}"><use href="/web/static/src/core/ui/person.svg#shirt"/></clipPath>
                    <rect width="156" height="240" fill="${this.color.shirt}" clip-path="url(#person_shirt_clip-${this._id})"/>
    
                    <use href="/web/static/src/core/ui/person.svg#shoes"/>
                    <clipPath id="person_shoes_clip-${this._id}"><use href="/web/static/src/core/ui/person.svg#shoes"/></clipPath>
                    <rect width="156" height="240" fill="${this.color.shoes}" clip-path="url(#person_shoes_clip-${this._id})"/>
    
                    <use href="/web/static/src/core/ui/person.svg#pants"/>
                    <clipPath id="person_pants_clip-${this._id}"><use href="/web/static/src/core/ui/person.svg#pants"/></clipPath>
                    <rect width="156" height="240" fill="${this.color.pants}" clip-path="url(#person_pants_clip-${this._id})"/>
    
                    <use href="/web/static/src/core/ui/person.svg#jacket"/>
                    <clipPath id="person_jacket_clip-${this._id}"><use href="/web/static/src/core/ui/person.svg#jacket"/></clipPath>
                    <rect width="156" height="240" fill="${this.color.jacket}" clip-path="url(#person_jacket_clip-${this._id})"/>
    
                    <use href="/web/static/src/core/ui/person.svg#skin"/>
                    <clipPath id="person_skin_clip-${this._id}"><use href="/web/static/src/core/ui/person.svg#skin"/></clipPath>
                    <rect width="156" height="240" fill="${this.color.skin}" clip-path="url(#person_skin_clip-${this._id})"/>
    
                    <use href="/web/static/src/core/ui/person.svg#hair"/>
                    <clipPath id="person_hair_clip-${this._id}"><use href="/web/static/src/core/ui/person.svg#hair"/></clipPath>
                    <rect width="156" height="240" fill="${this.color.hair}" clip-path="url(#person_hair_clip-${this._id})"/>
                    <use href="/web/static/src/core/ui/person.svg#light" clip-path="url(#person_hair_clip-${this._id})"/>
    
                    <use href="/web/static/src/core/ui/person.svg#head"/>
                </g>
            </g>`;
        return node;
    }
}

// physical items

class Item {
    constructor(layout, params) {
        this.layout = layout;
        this.state = {
            sprite: params.sprite,
            width: params.width,
            height: params.height,
            solid: params.solid || false,
            x: params.x,
            y: params.y,
            dx: params.dx || 0,
            dy: params.dy || 0,
            X: -1000,
            Y: -1000,
        };
        if (params.sprite === "person") {
            this.sprite = new SpritePerson(this.state.width, this.state.width/34*60, this.state.frame);
        } else if (params.sprite === "bonus") {
            this.sprite = new Sprite(this.state.width, this.state.height, this.state.frame);
        } else {
            this.sprite = new SpriteBox(this.state.width, this.state.height, this.state.frame);
        }
    }
    tick() {
        this.move();
        this.state.X = this.state.x + this.layout.state.x;
        this.state.Y = this.state.y + this.layout.state.y;
    }
    move() {
        if (this.state.dx) {
            this.state.x += this.state.dx;
        }
        if (this.state.dy) {
            this.state.y += this.state.dy;
        }
    }
    hit(x, y, width, height) {
        const dx = this.state.x - x;
        const dw = this.state.width/2 + width/2;

        const dy = this.state.y - y;
        const dh = this.state.height/2 + height/2;

        const precentX = Math.abs(dx) > dw ? 0 : - (Math.abs(dx) - dw) / dw * 100;
        const precentY = Math.abs(dy) > dh ? 0 : - (Math.abs(dy) - dh) / dh * 100;

        if (precentX > 0 && precentY > 0) {
            // repulsion from the lest collision
            return {
                precentX: precentX,
                precentY: precentY,
                x: - Math.sign(dx) * (dw - Math.abs(dx)),
                y: - Math.sign(dy) * (dh - Math.abs(dy)),
            };
        }
    }
    render() {
        if (!this.el) {
            this.el = document.createElementNS("http://www.w3.org/2000/svg", "g");
            if (this.state.sprite === "person") {
                const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
                g.setAttribute("transform", `translate(0 -12)`);
                this.el.appendChild(g);
                g.appendChild(this.sprite.render());
            } else {
                this.el.appendChild(this.sprite.render());
            }
        }

        this.el.setAttribute("transform", `translate(${this.state.X} ${this.state.Y})`);
        this.sprite.render();

        return this.el;
    }
    destroy() {
        if (this.el) {
            this.el.remove()
        }
    }
}

class Player extends Item {
    constructor(layout, params) {
        params.sprite = "person";
        super(layout, params);
        this.sprite.state.frame = "upStop";
    }
    setDirection() {
        const direction = this.layout.direction;
        const dy = this.layout.state.dy;
        const dx = this.layout.state.dx;
        const playerState = this.state;
        const spriteState = this.sprite.state;

        if (direction.x && direction.y) {
            direction.right = direction.x > playerState.X + playerState.width/2;
            direction.left = direction.x < playerState.X - playerState.width/2;
            direction.down = direction.y > playerState.Y + playerState.height/2;
            direction.up = direction.y < playerState.Y - playerState.height;
        }

        if (direction.up == direction.down) {
            playerState.dy = 0;
        } else if (direction.down) {
            spriteState.frame = "down";
            playerState.dy = Math.min(playerState.dy + 1, 5 + dy/2);
        } else if (direction.up) {
            spriteState.frame = "up";
            playerState.dy = Math.max(playerState.dy - 1, -5 - dy/2);
        }
        if (direction.left == direction.right) {
            playerState.dx = 0;
        } else if (direction.right) {
            spriteState.frame = "right";
            playerState.dx = Math.min(playerState.dx + 1, 5 + dx/2);
        } else if (direction.left) {
            spriteState.frame = "left";
            playerState.dx = Math.max(playerState.dx - 1, -5 - dx/2);
        }
        if (!playerState.dy && !playerState.dx && !spriteState.frame.includes("Stop")) {
            spriteState.frame += "Stop";
        }
    }
    move() {
        const initY = this.state.y;
        super.move();

        const layoutX = this.layout.state.x;
        const layoutY = this.layout.state.y;
        const layoutWidth = this.layout.width;
        const layoutHeight = this.layout.height;
        const state = this.state;
        const width = state.width;
        const height = state.height;

        if (state.y + layoutY > layoutHeight - height/2) {
            state.y = layoutHeight - height/2 - layoutY;
        } else if (state.y + layoutY < height/2) {
            state.y = height/2 - layoutY;
        }

        const x = state.x;
        const y = state.y;

        for (const item of this.layout.items) {
            const repulsion = item.hit(x, y, width, height);
            if (repulsion) {
                if (item.state.solid) {
                    if (repulsion.precentX < repulsion.precentY) {
                        state.x = x + repulsion.x;
                    } else {
                        state.y = y + repulsion.y;
                    }
                }
                this.layout._onHit(this, item, repulsion);
            }
        }

        if (state.x + layoutX > layoutWidth - state.width/2) {
            state.x = layoutWidth - state.width/2 - layoutX;
        } else if (state.x + layoutX < state.width/2) {
            state.x = state.width/2 - layoutX;
        }

        if (initY > state.y) {
            // push from the scrolling
            this.sprite.state.frame = "up";
        }
    }
}

// layout

class Layout {
    constructor(width, height) {
        this.width = width;
        this.height = height;
        this.score = 0;
        this.scores = [];
        this.items = [];
        this.direction = {};
        this.gameOver = false;
        this.running = false;
        this.mode = 'wait';
        this.player = new Player(this, {width: 34, height: 30, x: 300, y: 536});
        this.spritePerson = new SpritePerson(34, 60, "down");
        this.state = {x: 0, y: 0, dx: 0, dy: 3};

        this._onKeyDown = this._onKeyDown.bind(this);
        this._onKeyUp = this._onKeyUp.bind(this);
    }

    start() {
        for (const item of this.items) {
            item.destroy();
        }
        this.score = 0;
        this.items = [];
        Object.assign(this.state, {x: 0, y: 0, dx: 0, dy: 1});
        this.gameOver = false;
        Object.assign(this.player.state, {x: this.width/2, y: this.height - 64});
        this.player.sprite.colorize();
        this.spritePerson.colorize();

        if (this.running) {
            this.lastTick = new Date().getTime();
        } else {
            this.running = new Date().getTime();
            this.lastTick = this.running;
            this.run();
        }
        document.removeEventListener("keydown", (ev) => this._onKeyDown(ev));
        document.removeEventListener("keyup", (ev) => this._onKeyUp(ev));
        document.addEventListener("keydown", (ev) => this._onKeyDown(ev));
        document.addEventListener("keyup", (ev) => this._onKeyUp(ev));
    }

    stop() {
        this.running = false;
        this.mode = 'wait';
        document.removeEventListener("keydown", (ev) => this._onKeyDown(ev));
        document.removeEventListener("keyup", (ev) => this._onKeyUp(ev));
    }

    run() {
        if (!this.running) {
            return;
        }
        const time = new Date().getTime();
        const period = this.height <= 500 ? 20 : 17;  // slower for small screen
        let step = Math.min(5, Math.floor((((this.lastTick - this.running) % period) + time - this.lastTick) / period));
        this.lastTick = time;
        while (step > 0) {
            this.tick();
            step--;
        }
        this.render();
        requestAnimationFrame(() => this.run());
    }

    tick() {
        if (this.mode === 'wait') {
            return;
        }

        this.createItems();
        this.scroll();
        this.player.setDirection();

        for (const item of this.items.slice()) {
            item.tick();
            const isOut = item.state.y + this.state.y > this.height + item.height/2 ||
                item.state.y + this.state.y < -item.height/2 ||
                item.state.x + this.state.x > this.width + item.width/2 ||
                item.state.x + this.state.x < -item.width/2;
            if (isOut) {
                // unload items out of screen
                item.destroy();
                this.items.splice(this.items.indexOf(item), 1);
            }
        }
        this.player.tick();
    }

    createNode() {
        if (this.el) {
            return this.el;
        }
        const container = document.createElement("container");
        container.innerHTML = `
            <div class="o_loading_screen" style="cursor: default;">
                <svg width="${this.width}" height="${this.height}" xmlns="http://www.w3.org/2000/svg" style="display: none;">
                    <rect width="100%" height="100%" fill="#ffffff"/>
                    <filter id="noise2" x="0%" y="0%" width="100%" height="100%">
                        <feTurbulence stitchTiles="stitch" baseFrequency="0.05" seed="0"/>
                        <feColorMatrix in2="turbulence" type="saturate" values="0.10"/>
                    </filter>
                    <rect opacity="0.2" filter="url(#noise2)" width="100%" height="${this.height * 2 - 1}"/>
                    <rect opacity="0.2" filter="url(#noise2)" width="100%" height="${this.height * 2 - 1}"/>

                    <g><g/></g>

                    <g style="font-weight: bold;font-size: 16px;" fill="#000000">
                        <text x="${this.width - 156}" y="20">High score:</text>
                        <text x="${this.width - 64}" y="21"/>000000</text>
                        <text x="${this.width - 119}" y="40">Score:</text>
                        <text x="${this.width - 64}" y="41"/>000000</text>
                        <text id="gameover" x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" style="display: none; font-size: 40px;">Game over !</text>
                    </g>
                    <rect x="1" y="1" width="${this.width - 2}" height="${this.height - 2}" fill="none" stroke="#495057" stroke-width="2"/>
                </svg>
                <svg width="34" height="58" xmlns="http://www.w3.org/2000/svg"><g transform="translate(17 30)"/></svg>
            </div>`;
        this.el = container.firstElementChild;

        this.elemGame = this.el.querySelector("svg");
        this.elemItems = this.elemGame.querySelector("g g");
        this.elemHighscore = this.el.getElementsByTagName("text")[1];
        this.elemScore = this.el.getElementsByTagName("text")[3];
        this.elemGameover = this.el.getElementsByTagName("text")[4];

        this.el.addEventListener("click", (ev) => this._onClick(ev));
        this.elemGame.addEventListener("mousedown", (ev) => this._onMouseDown(ev));
        this.elemGame.addEventListener("mousemove", (ev) => this._onMouseDown(ev));
        this.elemGame.addEventListener("touchstart", (ev) => this._onClick(ev));
        this.elemGame.addEventListener("touchstart", (ev) => this._onTouchStart(ev));
        this.elemGame.addEventListener("touchmove", (ev) => this._onTouchStart(ev));
        this.elemGame.addEventListener("mouseup", () => (this._onMouseUp()));
        this.elemGame.addEventListener("touchend", () => (this._onMouseUp()));

        this.elemItems.parentNode.appendChild(this.player.render());
        this.elemGame.nextElementSibling.querySelector("g").appendChild(this.spritePerson.render());

        this.render();

        return this.el;
    }

    render() {
        if (!this.el) {
            return;
        }

        if (this.mode === 'wait') {
            if (this.elemGame.nextElementSibling.style.display === "none") {
                this.elemGame.style.display = "none";
                this.elemGame.nextElementSibling.style.display = "";
            }
            this.spritePerson.render();
            return;
        }

        this.player.render();

        this.elemScore.textContent =  ("000000" + Math.round(this.score)).slice(-6);
        this.elemHighscore.textContent = ("000000" + Math.round(Math.max(...this.scores, this.score))).slice(-6);

        for (const item of this.items) {
            if (!item.el) {
                this.elemItems.appendChild(item.render());
            } else {
                item.render();
            }
        }

        if (this.elemGame.nextElementSibling.style.display === "") {
            this.elemGame.style.display = "";
            this.elemGame.nextElementSibling.style.display = "none";
            this.elemGameBound = this.elemGame.getBoundingClientRect();

        }

        if (this.elemGameover.style.display !== (this.gameOver ? "" : "none")) {
            this.elemGameover.style.display = (this.gameOver ? "" : "none");
        }

        this.elemGame.querySelectorAll('rect')[1].setAttribute("transform", `translate(0 ${(this.state.y % (this.height * 2))})`);
        this.elemGame.querySelectorAll('rect')[2].setAttribute("transform", `translate(0 ${(this.state.y % (this.height * 2) - this.height * 2)})`);
    }

    createItems() {
        if (Math.random() < (0.03 + this.state.dy / 100) * (this.width / 600)) {
            const sprite = Math.random() > (0.6 + this.state.dy / 50) ? "bonus" : "box";
            const width = sprite === "box" ? 40 + (this.state.dy > 8 ? Math.random() * 80 : this.state.dy > 5 ? Math.random() * 20 : 0) : 31;
            const height = sprite === "box" ? width : 13;

            const itemParams = {
                sprite: sprite,
                width: width,
                height: height,
                x: this.state.x + Math.round(Math.random() * this.width),
                y: - this.state.y - height/2 + 1,
                solid: sprite === "box",
            };

            for (const other of this.items) {
                if (other.state.solid) {
                    const repulsion = other.hit(itemParams.x, itemParams.y, itemParams.width, itemParams.height);
                    if (repulsion?.x) {
                        itemParams.x += repulsion.x;
                    }
                }
            }

            this.items.push(new Item(this, itemParams));
        }
    }

    scroll() {
        if (this.state.dy < 10) {
            this.state.dy += 0.002;
        }
        this.state.x += this.state.dx;
        this.state.y += this.state.dy;

        this.score += (0.1 + Math.sqrt(this.state.dy));
    }


    _onHit(player, item, repulsion) {
        if (item.state.sprite === "bonus") {
            this.score += (this.state.dy > 8 ? 2000 : 1000);
            item.destroy();
            this.items.splice(this.items.indexOf(item), 1);
        } else if (item.state.solid && repulsion.y > 0) {
            if (player.state.y + this.state.y > this.height - player.state.height/2) {
                this.gameOver = true;
                this.running = false;
                this.scores.push(this.score);
            }
        }
    }

    _onClick(ev) {
        ev.preventDefault();
        if (this.mode === 'wait' || this.gameOver) {
            this.mode = 'play';
            this.start();
        }
    }

    _onMouseDown(ev) {
        ev.preventDefault();
        if (ev.buttons) {
            this.direction = {x: ev.pageX - this.elemGameBound.x, y: ev.pageY - this.elemGameBound.y};
        } else if (this.direction.x || this.direction.y) {
            this.direction = {};
        }
    }

    _onTouchStart(ev) {
        ev.preventDefault();
        this.direction = {x: ev.touches[0].pageX - this.elemGameBound.x, y: ev.touches[0].pageY - this.elemGameBound.y};
    }

    _onMouseUp() {
        this.direction = {};
    }

    _onKeyDown(ev) {
        if (ev.key === "ArrowLeft") {
            this.direction.left = true;
            this.direction.right = false;
        } else if (ev.key === "ArrowRight") {
            this.direction.right = true;
            this.direction.left = false;
        } else if (ev.key === "ArrowUp") {
            this.direction.up = true;
            this.direction.down = false;
        } else if (ev.key === "ArrowDown") {
            this.direction.down = true;
            this.direction.up = false;
        } else {
            if ((this.gameOver || this.mode === 'wait') && (ev.key === " " || ev.key === "Enter")) {
                this.mode = 'play';
                this.start();
            }
            return;
        }
    }

    _onKeyUp(ev) {
        if (ev.key === "ArrowLeft") {
            this.direction.left = false;
        } else if (ev.key === "ArrowRight") {
            this.direction.right = false;
        } else if (ev.key === "ArrowUp") {
            this.direction.up = false;
        } else if (ev.key === "ArrowDown") {
            this.direction.down = false;
        }
    }
}

export default class LoadingScreen {
    constructor() {
        const width = Math.min(600, window.innerWidth - 80);
        const height = Math.max(Math.min(600, window.innerHeight - 400), 400);
        this._layout = new Layout(width, height);
    }
    start() {
        this._layout.start();
    }
    stop() {
        this._layout.stop();
    }
    render() {
        return this._layout.createNode();
    }
}
