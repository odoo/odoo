<?xml version="1.0" encoding="utf-8"?>
<odoo>

<template id="event_track_location_display_speaker" name="Location Display Speaker">
    <div t-if="track.image or track.partner_name"
        t-attf-class="o_wevent_location_display_speaker d-inline-flex align-items-start gap-3 #{'o_wevent_location_display_speaker_live' if is_live else ''}">
        <div t-if="track.image" class="flex-shrink-0 rounded overflow-hidden" t-field="track.image"
            t-options="{'widget': 'image', 'class': 'o_wevent_location_display_speaker_image object-fit-cover', 'max_width': '256'}"/>
        <div>
            <h5 t-if="track.partner_name" t-attf-class="mb-0 #{'h3' if is_live else 'h4'}" t-field="track.partner_name"/>
            <div t-attf-class="text-white-75 #{'fs-4' if is_live else 'fs-5'}">
                <span t-if="track.partner_function" t-field="track.partner_function"/>
                <t t-if="track.partner_function and track.partner_company_name"> · </t>
                <span t-if="track.partner_company_name" t-field="track.partner_company_name"/>
            </div>
        </div>
    </div>
</template>

<template id="event_track_location_display_track" name="Location Display Track">
    <article t-attf-class="o_wevent_location_display_track #{'border rounded overflow-hidden' if is_live else ''} #{'bg-black-25' if is_live and location_display_background_url else ''} #{'border-bottom' if not is_live and is_last == False else ''}">
        <div t-attf-class="p-5 #{'px-0' if not is_live else 'px-4'} #{'bg-transparent text-white' if is_live and location_display_background_url else ''} #{'border-start border-5 border-primary' if is_live else ''}">
            <div class="d-flex flex-column gap-2">
                <time class="h4 mb-0 font-monospace" t-out="format_track_time(track)"/>
                <h2 t-attf-class="#{'mb-0' if not is_live else 'display-4-fs'}" t-field="track.name"/>
                <div t-if="is_live and track.tag_ids" class="d-flex flex-wrap align-items-center gap-1 fs-4">
                    <span t-foreach="track.tag_ids" t-as="tag" t-att-class="'badge rounded-pill o_color_%s' % (tag.color or 0)" t-out="tag.name"/>
                </div>
            </div>
            <div t-if="is_live" class="o_wevent_location_display_live_details mt-5">
                <div class="d-flex flex-wrap gap-4">
                    <t t-call="website_event_track.event_track_location_display_speaker"/>
                </div>
            </div>
            <div t-else="" class="d-flex gap-4 flex-wrap mt-4">
                <t t-call="website_event_track.event_track_location_display_speaker"/>
            </div>
        </div>
    </article>
</template>

<template id="event_track_location_display_empty_state" name="Location Display Empty State">
    <t t-if="next_track">
        <section t-attf-class="o_wevent_location_display_empty d-flex flex-column justify-content-center #{empty_section_classes or ''}"
            t-att-aria-labelledby="'o_wevent_location_display_empty_status' if live_status in ('none', 'finished') else 'o_wevent_location_display_empty_title'">
            <t t-if="live_status in ('none', 'finished')">
                <div>
                    <t t-if="live_status == 'none'">
                        <h2 id="o_wevent_location_display_empty_status" class="display-4-fs">No talks today</h2>
                        <div class="fs-3">Nothing is scheduled in this room today.</div>
                    </t>
                    <t t-else="">
                        <h2 id="o_wevent_location_display_empty_status" class="display-4-fs">That’s all for today</h2>
                        <div class="fs-3">Thanks for joining us.</div>
                    </t>
                </div>
            </t>
            <div t-att-class="'mt-5' if live_status in ('none', 'finished') else None">
                <span class="badge bg-primary text-uppercase font-monospace mb-3 fs-5" t-out="formatted_track_day_label"/>
                <div t-attf-class="o_wevent_location_display_upcoming_list border rounded px-4 #{'bg-black-25 text-white' if location_display_background_url else ''}">
                    <t t-call="website_event_track.event_track_location_display_track" track="next_track" is_live="False"/>
                </div>
            </div>
        </section>
    </t>
    <t t-else="">
        <section t-attf-class="o_wevent_location_display_empty d-flex flex-column align-items-center justify-content-center text-center #{empty_section_classes or 'flex-grow-1'}">
            <h2 t-attf-class="#{'display-4-fs' if live_status != 'live' else ''}">End of the day</h2>
            <div t-attf-class="#{'fs-3' if live_status != 'live' else 'fs-4'}">Thanks for joining us.</div>
        </section>
    </t>
</template>

<template id="event_track_location_display_content" name="Location Display Content">
    <main aria-live="polite" aria-atomic="true"
        t-att-data-background-image-url="location_display_background_url"
        t-att-data-current-time="current_time_label"
        t-attf-class="o_wevent_location_display_content d-flex flex-column flex-grow-1 #{'pt-4 pt-lg-5' if live_status == 'live' else ''}">
        <t t-if="live_status in ('none', 'finished')">
            <t t-call="website_event_track.event_track_location_display_empty_state"/>
        </t>
        <t t-elif="live_status in ('live', 'gap')">
            <section class="o_wevent_location_display_live"
                t-att-aria-label="'Live now' if live_status == 'live' else None"
                t-att-aria-labelledby="'o_wevent_location_display_live_title' if live_status == 'gap' else None">
                <t t-if="live_status == 'live'">
                    <h2 id="o_wevent_location_display_upcoming_title" class="my-3 h1">
                        <span class="o_wevent_location_display_live_badge d-inline-block align-middle me-2 bg-danger rounded-pill"/>Live Now
                    </h2>
                    <t t-call="website_event_track.event_track_location_display_track" track="live_track" is_live="True"/>
                </t>
                <div t-elif="live_status == 'gap'">
                    <h2 id="o_wevent_location_display_live_title" class="display-4-fs">Nothing planned right now</h2>
                    <div class="fs-3">The next session will begin shortly.</div>
                </div>
            </section>

            <section t-if="upcoming_tracks" class="o_wevent_location_display_upcoming mt-5" aria-labelledby="o_wevent_location_display_upcoming_title">
                <h2 id="o_wevent_location_display_upcoming_title" class="my-3">Coming up</h2>
                <div t-attf-class="o_wevent_location_display_upcoming_list border rounded px-4 #{'bg-black-25 text-white' if location_display_background_url else ''}">
                    <t t-foreach="upcoming_tracks" t-as="track">
                        <t t-call="website_event_track.event_track_location_display_track" is_live="False" is_last="track_last"/>
                    </t>
                </div>
            </section>
            <t t-elif="live_status == 'live'">
                <t t-set="empty_section_classes" t-value="'mt-5'"/>
                <t t-call="website_event_track.event_track_location_display_empty_state"/>
            </t>
        </t>
    </main>
</template>

<template id="event_track_location_display" name="Event Location Display">
    <t t-set="no_header" t-value="True"/>
    <t t-set="no_footer" t-value="True"/>
    <t t-set="no_livechat" t-value="True"/>
    <t t-set="no_cookies_bar" t-value="True"/>
    <t t-call="website.layout">
        <div id="wrap"
            t-attf-class="o_wevent_location_display vh-100 overflow-hidden d-flex flex-column p-3 p-md-4 p-xl-5 o_cc o_cc5 #{'o_wevent_location_display_has_background' if location_display_background_url else ''}"
            t-att-style="'--o-wevent-location-display-background-image: url(%s);' % location_display_background_url if location_display_background_url else None"
            t-att-data-refresh-url="'/event/%s/location-display/%s/content' % (event.id, location_id)">
            <header class="d-flex align-items-center justify-content-between gap-3 mb-5">
                <span t-field="website.logo"
                    t-options="{'widget': 'image', 'max_height': '80'}"
                    class="o_wevent_location_display_logo"
                    t-att-aria-label="'Logo of %s' % website.name"
                    t-att-title="website.name"/>
                <div class="text-end">
                    <time class="o_wevent_location_display_now d-block fs-5 font-monospace mb-1" t-out="current_time_label"/>
                    <h1 class="h2 mb-0"><i class="oi me-2" data-icon="location_on" aria-hidden="true"/><t t-out="location_name"/></h1>
                </div>
            </header>
            <t t-call="website_event_track.event_track_location_display_content"/>
            <div class="o_wevent_location_display_fade position-fixed bottom-0 start-0 end-0" aria-hidden="true"/>
            <div class="o_wevent_location_display_refresh_status position-fixed end-0 bottom-0 z-1 m-2 px-2 py-1 text-warning-emphasis small fw-semibold d-none"
                role="status">
                <i class="oi me-1 align-middle" data-icon="link_off" aria-hidden="true"/>
                <span>Last updated at</span>
                <time/>
            </div>
        </div>
    </t>
</template>

<template id="event_track_location_display_no_cookies_bar" inherit_id="website.cookies_bar">
    <xpath expr="//div[@id='website_cookies_bar']" position="attributes">
        <attribute name="t-if" add="not no_cookies_bar" separator="and"/>
    </xpath>
</template>

</odoo>
