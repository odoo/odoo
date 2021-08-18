odoo.define('flexipharmacy.VideoSlider', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { useState } = owl.hooks;

    class VideoSlider extends PosComponent {
        constructor() {
            super(...arguments);
            this.state = useState({activeVideo: 0});
        }
        nextSlide(){
            if (this.state.activeVideo === this.videoList.length - 1) {
                this.state.activeVideo = 0;
                return;
            }
            this.state.activeVideo = this.state.activeVideo + 1;
        }
        prevSlide(){
            if (this.state.activeVideo === 0) {
                this.state.activeVideo = this.videoList.length - 1;
                return;
            }
            this.state.activeVideo = this.state.activeVideo - 1;
        }
        get videoList(){
            return this.env.pos.ad_video_ids ? this.env.pos.ad_video_ids : []
        }
        get width(){
            return this.props.width;
        }
        get videoSrc(){
            return "https://www.youtube.com/embed/"+this.videoList[this.state.activeVideo]+"?playlist="+this.videoList[this.state.activeVideo]+";loop=1;autoplay=1;mute=1;controls=0;autohide=1;showinfo=0;"
        }
    }
    VideoSlider.template = 'VideoSlider';

    Registries.Component.add(VideoSlider);

    return VideoSlider;
});
