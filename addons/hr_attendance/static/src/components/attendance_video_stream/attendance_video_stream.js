import { Component, onMounted, onWillStart, onWillUnmount, signal, t, useProps } from "@odoo/owl";
import { useCamera } from "@hr_attendance/components/hooks/use_camera";

export class AttendanceVideoStream extends Component {
    static template = "hr_attendance.AttendanceVideoStream";

    props = useProps({
        height: t.number(),
        width: t.number(),
        exposeCameraCapture: t.function(),
        onStreamStateChange: t.function(),
    });

    attendanceVideoRef = signal.ref();

    setup() {
        this.camera = useCamera({
            width: this.props.width,
            height: this.props.height,
        });

        onWillStart(async () => {
            await this.camera.start();
            this.streamAvailable = this.camera.isStreamAvailable();
        });

        onMounted(async () => {
            this.props.onStreamStateChange(this.streamAvailable);
            if (this.streamAvailable) {
                this.props.exposeCameraCapture(this.camera.capturePicture);
            }
            await this.camera.attachStreamToVideo(this.attendanceVideoRef());
        });

        onWillUnmount(() => {
            this.camera.stop();
            this.props.exposeCameraCapture(null);
            this.props.onStreamStateChange(false);
        });
    }
}
