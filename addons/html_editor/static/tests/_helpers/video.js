// Valid provider URLs; the base URL is also used by media and background video tests.
export const VIDEO_URLS = {
    youtube: {
        base: "https://www.youtube.com/watch?v=jar2eqeMNjc",
        short: "https://www.youtube.com/shorts/qAgW3oG7Zmc",
        live: "https://www.youtube.com/live/fmVNEoxr7iU?feature=shared",
        mobile: "https://m.youtube.com/watch?v=xCvFZrrQq7k",
        minified: "youtu.be/xCvFZrrQq7k",
        noCookie: "https://www.youtube-nocookie.com/watch?v=xCvFZrrQq7k",
        embed: "https://www.youtube.com/embed/xCvFZrrQq7k",
        params: "https://www.youtube.com/watch?v=xCvFZrrQq7k&t=62&autoplay=1&loop=1&controls=0&fs=0",
        embedParams:
            "https://www.youtube.com/embed/xCvFZrrQq7k?start=62&autoplay=1&loop=1&controls=0&fs=0",
    },
    instagram: {
        base: "https://www.instagram.com/p/B6dXGTxggTG",
        minified: "instagr.am/p/B6dXGTxggTG/",
        reel: "https://www.instagram.com/reel/B6dXGTxggTG/",
        reel2: "https://www.instagram.com/odoo.official/reel/B6dXGTxggTG/",
        reels: "https://www.instagram.com/reels/DPD1qwXDBwy/",
        embed: "https://www.instagram.com/p/B6dXGTxggTG/embed/",
    },
    facebook: {
        base: "https://www.facebook.com/username/videos/2206239373151307/",
        watch: "facebook.com/watch/?v=2206239373151307",
        reel: "https://www.facebook.com/username/reel/2206239373151307/",
        embed: "https://www.facebook.com/plugins/video.php?href=https%3A%2F%2Fwww.facebook.com%2Fusername%2Fvideos%2F2206239373151307%2F",
    },
    gDrive: {
        base: "https://drive.google.com/file/d/1A2B3C4D5E6F7G8H9I0J/view?usp=sharing",
        embed: "drive.google.com/file/d/1A2B3C4D5E6F7G8H9I0J/preview",
    },
    dailymotion: {
        base: "https://www.dailymotion.com/video/x7svr6t",
        extra: "https://www.dailymotion.com/video/x2jvvep_hakan-yukur-klip_sport",
        embed: "https://geo.dailymotion.com/player.html?video=x7svr6t",
        minified: "dai.ly/x7svr6t",
        params: "https://www.dailymotion.com/video/x7svr6t?startTime=62",
        embedParams: "https://geo.dailymotion.com/player.html?video=x7svr6t&startTime=62",
        // This is the old embed url of dailymotion,
        // we keep supporting it for backward compatibility reasons,
        // but it should not be used anymore.
        dailymotion_old_embed: "https://www.dailymotion.com/embed/video/x578has?autoplay=1",
    },
    vimeo: {
        base: "https://vimeo.com/395399735",
        unlisted: "https://vimeo.com/795669787/0763fdb816", // Not sure if this format is still relevant
        embed: "https://player.vimeo.com/video/395399735",
        embedUnlisted: "https://player.vimeo.com/video/795669787?h=0763fdb816",
        params: "vimeo.com/395399735?autoplay=1#t=62",
        embedParams:
            "https://player.vimeo.com/video/395399735?controls=0&fullscreen=1&autoplay=1#t=62",
    },
    twitch: {
        base: "https://www.twitch.tv/videos/1064007405",
        clip: "https://www.twitch.tv/monstercat/clip/UnrulyShySalamanderPogChamp?filter=clips&range=7d&sort=time",
        embed: "https://player.twitch.tv/?video=1064007405&parent=example.com",
        embedClip:
            "https://clips.twitch.tv/embed?clip=UnrulyShySalamanderPogChamp&parent=example.com",
        params: "twitch.tv/videos/1064007405?time=62&autoplay=true&muted=true",
        embedParams:
            "https://player.twitch.tv/?video=1064007405&parent=example.com&time=62&autoplay=true&muted=true",
    },
    loom: {
        base: "https://www.loom.com/share/e5b8c04bca094dd8a5507925ab887002",
        embed: "https://www.loom.com/embed/e5b8c04bca094dd8a5507925ab887002",
        Params: "loom.com/share/e5b8c04bca094dd8a5507925ab887002?autoplay=1&t=62",
        embedParams:
            "https://www.loom.com/embed/e5b8c04bca094dd8a5507925ab887002?autoplay=1&t=62s&hide_share=1&hideEmbedTopBar=0&hide_title=0&hide_owner=1&hide_speed=1&fullscreen=1",
    },
};
