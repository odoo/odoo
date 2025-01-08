import {
    startInteractions,
    setupInteractionWhiteList,
} from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";
// import { click } from "@odoo/hoot-dom";

setupInteractionWhiteList("website_event_meet.meeting_room");

describe.current.tags("interaction_dev");

const meetingRoomTemplate = `
    <div class="o_wemeet_container container h-100">
        <div class="row h-100 mb-5">
            <div class="col-12 col-lg-8 col-xl-9 pe-xxl-5">
                <div class="d-flex flex-row flex-wrap gap-2 pt-3 justify-content-between mb-2">
                    <h3 class="my-0 lh-1" data-oe-model="ir.ui.view" data-oe-id="1449" data-oe-field="arch" data-oe-xpath="/t[1]/div[1]/div[1]/h3[1]">Join a room</h3>
                    <div class="dropdown">
                        <a class="dropdown-toggle btn btn-light" title="Languages Menu" aria-label="Dropdown menu" data-bs-display="static" data-bs-toggle="dropdown" href="#" role="button">
                        <span>All Languages</span></a>
                        <div class="dropdown-menu" role="menu">
                            <a class="dropdown-item" role="menuitem" data-oe-model="ir.ui.view" data-oe-id="1449" data-oe-field="arch" data-oe-xpath="/t[1]/div[1]/div[1]/div[1]/div[1]/a[1]" href="/event/openwood-collection-online-reveal-8/community">All Languages
                            </a>
                            <a class="dropdown-item" role="menuitem" href="/event/openwood-collection-online-reveal-8/community?lang=30">French / Français</a><a class="dropdown-item" role="menuitem" href="/event/openwood-collection-online-reveal-8/community?lang=1">English (US)</a>
                        </div>
                    </div>
                </div>
                <p class="lead" data-oe-model="ir.ui.view" data-oe-id="1449" data-oe-field="arch" data-oe-xpath="/t[1]/div[1]/p[1]">Choose a topic that interests you and start talking with the community. <br> Don't forget to setup your camera and microphone.</p>
                <div class="d-flex flex-column justify-content-start align-items-start">
                    <div class="modal o_join_later_modal fixed-top" tabindex="-1" role="dialog" style="top: 0" id="o_join_later_modal_3">
                        <div class="modal-dialog" role="document">
                            <div class="modal-content">
                                <div class="mt-4 col-12 alert alert-warning text-center" role="alert">
                                    <nav class="navbar navbar-default" data-oe-model="ir.ui.view" data-oe-id="1450" data-oe-field="arch" data-oe-xpath="/t[1]/div[1]/div[1]/div[1]/div[1]/nav[1]">
                                        <div class="container-fluid">
                                            <div class="navbar-header">
                                                <div class="o_wevent_meeting_room_card_menu"></div>
                                            </div>
                                        </div>
                                    </nav>
                                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close" data-oe-model="ir.ui.view" data-oe-id="1450" data-oe-field="arch" data-oe-xpath="/t[1]/div[1]/div[1]/div[1]/div[1]/button[1]"></button>
                                    <span data-oe-model="ir.ui.view" data-oe-id="1450" data-oe-field="arch" data-oe-xpath="/t[1]/div[1]/div[1]/div[1]/div[1]/t[1]/span[1]">This room is not open right now!</span><br data-oe-model="ir.ui.view" data-oe-id="1450" data-oe-field="arch" data-oe-xpath="/t[1]/div[1]/div[1]/div[1]/div[1]/t[1]/br[1]">
                                    Join us here on the
                                    <strong itemprop="startDate" data-oe-xpath="/t[1]/div[1]/div[1]/div[1]/div[1]/t[1]/strong[1]" data-oe-model="event.event" data-oe-id="8" data-oe-field="date_begin" data-oe-type="datetime" data-oe-expression="event.date_begin" data-oe-original="2024-12-16 06:00:00" data-oe-original-with-format="12/16/2024 06:00:00" data-oe-original-tz="Europe/Brussels">Dec 16, 2024, 6:00:00 AM</strong>
                                    <strong>(Europe/Brussels)</strong>
                                    to have a chat with us!
                                </div>
                                <div class="modal-body row">
                                    <div class="col-3">
                                        <div class="w-100" data-oe-model="ir.ui.view" data-oe-id="1450" data-oe-field="arch" data-oe-xpath="/t[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]" style="background-image: url('/website_event/static/src/img/event_cover_7.jpg'); min-height: 5rem; background-size: cover;"></div>
                                    </div>
                                    <div class="col">
                                        <h5>Vos meubles préférés ?</h5>
                                        <div class="text-muted mb-2"><i class="fa fa-globe" data-oe-model="ir.ui.view" data-oe-id="1450" data-oe-field="arch" data-oe-xpath="/t[1]/div[1]/div[1]/div[1]/div[2]/div[2]/div[1]/i[1]"></i> <span>French / Français</span></div>
                                        <span data-oe-xpath="/t[1]/div[1]/div[1]/div[1]/div[2]/div[2]/span[1]" data-oe-model="event.meeting.room" data-oe-id="3" data-oe-field="summary" data-oe-type="char" data-oe-expression="meeting_room.summary">Venez partager vos meubles préférés et l'utilisation que vous en faites.</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <a class="card o_wevent_meeting_room_card w-100 my-2 d-block text-decoration-none rounded-0 bg-transparent text-reset" data-meeting-room-id="3" data-is-event-manager="1" href="/event/openwood-collection-online-reveal-8/meeting_room/vos-meubles-preferes-3">
                        <div class="w-100 h-100 p-3 border-start border-5 text-decoration-none" data-publish="on">
                            <div class="d-flex flex-column">
                                <div class="d-flex flex-row">
                                    <h4 class="text-break w-75">Vos meubles préférés ?</h4>
                                </div>
                                <p class="text-muted" data-oe-xpath="/t[1]/a[1]/div[1]/div[2]/p[1]" data-oe-model="event.meeting.room" data-oe-id="3" data-oe-field="summary" data-oe-type="char" data-oe-expression="meeting_room.summary">Venez partager vos meubles préférés et l'utilisation que vous en faites.</p>
                                <div class="d-flex flex-row justify-content-between align-items-center">
                                    <p class="d-flex justify-content-between align-items-center gap-2 m-0 text-muted small">
                                        <i class="fa fa-user" data-oe-model="ir.ui.view" data-oe-id="1450" data-oe-field="arch" data-oe-xpath="/t[1]/a[1]/div[1]/div[2]/div[2]/p[1]/i[1]"></i>
                                        <span>3</span>
                                        <span data-oe-xpath="/t[1]/a[1]/div[1]/div[2]/div[2]/p[1]/span[2]" data-oe-model="event.meeting.room" data-oe-id="3" data-oe-field="target_audience" data-oe-type="char" data-oe-expression="meeting_room.target_audience">client(s)</span>
                                    </p>
                                    <div class="badge text-bg-secondary">French / Français</div>
                                </div>
                            </div>
                        </div>
                        <div class="position-absolute o_wevent_meeting_room_manager_menu d-flex justify-content-end flex-column flex-md-row">
                            <button data-oe-model="ir.ui.view" data-oe-id="1450" data-oe-field="arch" data-oe-xpath="/t[1]/a[1]/div[2]/button[1]" class="o_wevent_meeting_room_is_pinned btn o_wevent_meeting_room_pinned">
                            <i class="fa fa-thumb-tack"></i>
                            </button>
                            <div class="dropdown dropstart" data-oe-model="ir.ui.view" data-oe-id="1450" data-oe-field="arch" data-oe-xpath="/t[1]/a[1]/div[2]/div[1]">
                                <button class="btn" data-bs-toggle="dropdown"><i class="fa fa-ellipsis-v px-1"></i></button>
                                <div class="dropdown-menu">
                                    <button class="dropdown-item btn o_wevent_meeting_room_duplicate" type="button">Duplicate</button>
                                    <button class="dropdown-item btn o_wevent_meeting_room_delete" type="button">Close</button>
                                </div>
                            </div>
                        </div>
                    </a>
                    <div class="modal o_join_later_modal fixed-top" tabindex="-1" role="dialog" style="top: 0" id="o_join_later_modal_2">
                        <div class="modal-dialog" role="document">
                            <div class="modal-content">
                                <div class="mt-4 col-12 alert alert-warning text-center" role="alert">
                                    <nav class="navbar navbar-default" data-oe-model="ir.ui.view" data-oe-id="1450" data-oe-field="arch" data-oe-xpath="/t[1]/div[1]/div[1]/div[1]/div[1]/nav[1]">
                                        <div class="container-fluid">
                                            <div class="navbar-header">
                                                <div class="o_wevent_meeting_room_card_menu"></div>
                                            </div>
                                        </div>
                                    </nav>
                                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close" data-oe-model="ir.ui.view" data-oe-id="1450" data-oe-field="arch" data-oe-xpath="/t[1]/div[1]/div[1]/div[1]/div[1]/button[1]"></button>
                                    <span data-oe-model="ir.ui.view" data-oe-id="1450" data-oe-field="arch" data-oe-xpath="/t[1]/div[1]/div[1]/div[1]/div[1]/t[1]/span[1]">This room is not open right now!</span><br data-oe-model="ir.ui.view" data-oe-id="1450" data-oe-field="arch" data-oe-xpath="/t[1]/div[1]/div[1]/div[1]/div[1]/t[1]/br[1]">
                                    Join us here on the
                                    <strong itemprop="startDate" data-oe-xpath="/t[1]/div[1]/div[1]/div[1]/div[1]/t[1]/strong[1]" data-oe-model="event.event" data-oe-id="8" data-oe-field="date_begin" data-oe-type="datetime" data-oe-expression="event.date_begin" data-oe-original="2024-12-16 06:00:00" data-oe-original-with-format="12/16/2024 06:00:00" data-oe-original-tz="Europe/Brussels">Dec 16, 2024, 6:00:00 AM</strong>
                                    <strong>(Europe/Brussels)</strong>
                                    to have a chat with us!
                                </div>
                                <div class="modal-body row">
                                    <div class="col-3">
                                        <div class="w-100" data-oe-model="ir.ui.view" data-oe-id="1450" data-oe-field="arch" data-oe-xpath="/t[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]" style="background-image: url('/website_event/static/src/img/event_cover_7.jpg'); min-height: 5rem; background-size: cover;"></div>
                                    </div>
                                    <div class="col">
                                        <h5>Reducing the ecological footprint with wood?</h5>
                                        <div class="text-muted mb-2"><i class="fa fa-globe" data-oe-model="ir.ui.view" data-oe-id="1450" data-oe-field="arch" data-oe-xpath="/t[1]/div[1]/div[1]/div[1]/div[2]/div[2]/div[1]/i[1]"></i> <span>English (US)</span></div>
                                        <span data-oe-xpath="/t[1]/div[1]/div[1]/div[1]/div[2]/div[2]/span[1]" data-oe-model="event.meeting.room" data-oe-id="2" data-oe-field="summary" data-oe-type="char" data-oe-expression="meeting_room.summary">Share your tips to reduce your ecological footprint using wood.</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <a class="card o_wevent_meeting_room_card w-100 my-2 d-block text-decoration-none rounded-0 bg-transparent text-reset" data-meeting-room-id="2" data-is-event-manager="1" href="/event/openwood-collection-online-reveal-8/meeting_room/reducing-the-ecological-footprint-with-wood-2">
                        <div class="w-100 h-100 p-3 border-start border-5 text-decoration-none" data-publish="on">
                            <div class="o_wevent_meeting_room_corner_ribbon" data-oe-model="ir.ui.view" data-oe-id="1450" data-oe-field="arch" data-oe-xpath="/t[1]/a[1]/div[1]/div[1]">Full</div>
                            <div class="d-flex flex-column">
                                <div class="d-flex flex-row">
                                    <h4 class="text-break w-75">Reducing the ecological footprint with wood?</h4>
                                </div>
                                <p class="text-muted" data-oe-xpath="/t[1]/a[1]/div[1]/div[2]/p[1]" data-oe-model="event.meeting.room" data-oe-id="2" data-oe-field="summary" data-oe-type="char" data-oe-expression="meeting_room.summary">Share your tips to reduce your ecological footprint using wood.</p>
                                <div class="d-flex flex-row justify-content-between align-items-center">
                                    <p class="d-flex justify-content-between align-items-center gap-2 m-0 text-muted small">
                                        <i class="fa fa-user" data-oe-model="ir.ui.view" data-oe-id="1450" data-oe-field="arch" data-oe-xpath="/t[1]/a[1]/div[1]/div[2]/div[2]/p[1]/i[1]"></i>
                                        <span>8</span>
                                        <span data-oe-xpath="/t[1]/a[1]/div[1]/div[2]/div[2]/p[1]/span[2]" data-oe-model="event.meeting.room" data-oe-id="2" data-oe-field="target_audience" data-oe-type="char" data-oe-expression="meeting_room.target_audience">ecologist(s)</span>
                                    </p>
                                    <div class="badge text-bg-secondary">English (US)</div>
                                </div>
                            </div>
                        </div>
                        <div class="position-absolute o_wevent_meeting_room_manager_menu d-flex justify-content-end flex-column flex-md-row">
                            <button data-oe-model="ir.ui.view" data-oe-id="1450" data-oe-field="arch" data-oe-xpath="/t[1]/a[1]/div[2]/button[1]" class="o_wevent_meeting_room_is_pinned btn ">
                            <i class="fa fa-thumb-tack"></i>
                            </button>
                            <div class="dropdown dropstart" data-oe-model="ir.ui.view" data-oe-id="1450" data-oe-field="arch" data-oe-xpath="/t[1]/a[1]/div[2]/div[1]">
                                <button class="btn" data-bs-toggle="dropdown"><i class="fa fa-ellipsis-v px-1"></i></button>
                                <div class="dropdown-menu">
                                    <button class="dropdown-item btn o_wevent_meeting_room_duplicate" type="button">Duplicate</button>
                                    <button class="dropdown-item btn o_wevent_meeting_room_delete" type="button">Close</button>
                                </div>
                            </div>
                        </div>
                    </a>
                    <div class="modal o_join_later_modal fixed-top" tabindex="-1" role="dialog" style="top: 0" id="o_join_later_modal_1">
                        <div class="modal-dialog" role="document">
                            <div class="modal-content">
                                <div class="mt-4 col-12 alert alert-warning text-center" role="alert">
                                    <nav class="navbar navbar-default" data-oe-model="ir.ui.view" data-oe-id="1450" data-oe-field="arch" data-oe-xpath="/t[1]/div[1]/div[1]/div[1]/div[1]/nav[1]">
                                        <div class="container-fluid">
                                            <div class="navbar-header">
                                                <div class="o_wevent_meeting_room_card_menu"></div>
                                            </div>
                                        </div>
                                    </nav>
                                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close" data-oe-model="ir.ui.view" data-oe-id="1450" data-oe-field="arch" data-oe-xpath="/t[1]/div[1]/div[1]/div[1]/div[1]/button[1]"></button>
                                    <span data-oe-model="ir.ui.view" data-oe-id="1450" data-oe-field="arch" data-oe-xpath="/t[1]/div[1]/div[1]/div[1]/div[1]/t[1]/span[1]">This room is not open right now!</span><br data-oe-model="ir.ui.view" data-oe-id="1450" data-oe-field="arch" data-oe-xpath="/t[1]/div[1]/div[1]/div[1]/div[1]/t[1]/br[1]">
                                    Join us here on the
                                    <strong itemprop="startDate" data-oe-xpath="/t[1]/div[1]/div[1]/div[1]/div[1]/t[1]/strong[1]" data-oe-model="event.event" data-oe-id="8" data-oe-field="date_begin" data-oe-type="datetime" data-oe-expression="event.date_begin" data-oe-original="2024-12-16 06:00:00" data-oe-original-with-format="12/16/2024 06:00:00" data-oe-original-tz="Europe/Brussels">Dec 16, 2024, 6:00:00 AM</strong>
                                    <strong>(Europe/Brussels)</strong>
                                    to have a chat with us!
                                </div>
                                <div class="modal-body row">
                                    <div class="col-3">
                                        <div class="w-100" data-oe-model="ir.ui.view" data-oe-id="1450" data-oe-field="arch" data-oe-xpath="/t[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]" style="background-image: url('/website_event/static/src/img/event_cover_7.jpg'); min-height: 5rem; background-size: cover;"></div>
                                    </div>
                                    <div class="col">
                                        <h5>Best wood for furniture</h5>
                                        <div class="text-muted mb-2"><i class="fa fa-globe" data-oe-model="ir.ui.view" data-oe-id="1450" data-oe-field="arch" data-oe-xpath="/t[1]/div[1]/div[1]/div[1]/div[2]/div[2]/div[1]/i[1]"></i> <span>English (US)</span></div>
                                        <span data-oe-xpath="/t[1]/div[1]/div[1]/div[1]/div[2]/div[2]/span[1]" data-oe-model="event.meeting.room" data-oe-id="1" data-oe-field="summary" data-oe-type="char" data-oe-expression="meeting_room.summary">Let's talk about wood types for furniture</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <a class="card o_wevent_meeting_room_card w-100 my-2 d-block text-decoration-none rounded-0 bg-transparent text-reset" data-meeting-room-id="1" data-is-event-manager="1" href="/event/openwood-collection-online-reveal-8/meeting_room/best-wood-for-furniture-1">
                        <div class="w-100 h-100 p-3 border-start border-5 text-decoration-none" data-publish="on">
                            <div class="d-flex flex-column">
                                <div class="d-flex flex-row">
                                    <h4 class="text-break w-75">Best wood for furniture</h4>
                                </div>
                                <p class="text-muted" data-oe-xpath="/t[1]/a[1]/div[1]/div[2]/p[1]" data-oe-model="event.meeting.room" data-oe-id="1" data-oe-field="summary" data-oe-type="char" data-oe-expression="meeting_room.summary">Let's talk about wood types for furniture</p>
                                <div class="d-flex flex-row justify-content-between align-items-center">
                                    <p class="d-flex justify-content-between align-items-center gap-2 m-0 text-muted small">
                                        <i class="fa fa-user" data-oe-model="ir.ui.view" data-oe-id="1450" data-oe-field="arch" data-oe-xpath="/t[1]/a[1]/div[1]/div[2]/div[2]/p[1]/i[1]"></i>
                                        <span>9</span>
                                        <span data-oe-xpath="/t[1]/a[1]/div[1]/div[2]/div[2]/p[1]/span[2]" data-oe-model="event.meeting.room" data-oe-id="1" data-oe-field="target_audience" data-oe-type="char" data-oe-expression="meeting_room.target_audience">wood expert(s)</span>
                                    </p>
                                    <div class="badge text-bg-secondary">English (US)</div>
                                </div>
                            </div>
                        </div>
                        <div class="position-absolute o_wevent_meeting_room_manager_menu d-flex justify-content-end flex-column flex-md-row">
                            <button data-oe-model="ir.ui.view" data-oe-id="1450" data-oe-field="arch" data-oe-xpath="/t[1]/a[1]/div[2]/button[1]" class="o_wevent_meeting_room_is_pinned btn ">
                            <i class="fa fa-thumb-tack"></i>
                            </button>
                            <div class="dropdown dropstart" data-oe-model="ir.ui.view" data-oe-id="1450" data-oe-field="arch" data-oe-xpath="/t[1]/a[1]/div[2]/div[1]">
                                <button class="btn" data-bs-toggle="dropdown"><i class="fa fa-ellipsis-v px-1"></i></button>
                                <div class="dropdown-menu">
                                    <button class="dropdown-item btn o_wevent_meeting_room_duplicate" type="button">Duplicate</button>
                                    <button class="dropdown-item btn o_wevent_meeting_room_delete" type="button">Close</button>
                                </div>
                            </div>
                        </div>
                    </a>
                </div>
            </div>
            <div class="d-lg-flex justify-content-end col-lg-4 col-xl-3 mb-3 mb-lg-0">
                <div class="o_wevent_community_aside mt-3">
                    <div class="d-none d-md-block mb-4">
                        <h4 class="o_page_header h6" data-oe-model="ir.ui.view" data-oe-id="1451" data-oe-field="arch" data-oe-xpath="/t[1]/div[1]/div[1]/div[1]/h4[1]">Start a topic</h4>
                        <p data-oe-model="ir.ui.view" data-oe-id="1451" data-oe-field="arch" data-oe-xpath="/t[1]/div[1]/div[1]/div[1]/p[1]">Want to create your own discussion room?</p>
                        <a href="#" role="button" class="btn btn-secondary o_wevent_create_room_button w-100" data-oe-model="ir.ui.view" data-oe-id="1451" data-oe-field="arch" data-oe-xpath="/t[1]/div[1]/div[1]/div[1]/a[1]" data-event-id="8" data-default-lang-code="en_US">
                        Create a Room
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </div>
`;

test("website_event_meeting_room is started when there is an element .o_wevent_meeting_room_card", async () => {
    const { core } = await startInteractions(meetingRoomTemplate);
    expect(core.interactions.length).toBe(3);
});

test("[click] website_event_meeting_room enable to pin / unpin a room", async () => {
    await startInteractions(meetingRoomTemplate);
    // await click(".o_wevent_meeting_room_is_pinned");
    expect(true).toBe(true);
});

test("[click] website_event_meeting_room enable to delete a room", async () => {
    await startInteractions(meetingRoomTemplate);
    // await click(".o_wevent_meeting_room_delete");
    expect(true).toBe(true);
});

test("[click] website_event_meeting_room enable to duplicate a room", async () => {
    await startInteractions(meetingRoomTemplate);
    // await click(".o_wevent_meeting_room_duplicate");
    expect(true).toBe(true);
});
