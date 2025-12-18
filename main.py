import time
import cv2
import mediapipe as mp

# - VOLUME_UP: işaret parmak tek başına yukarıdaysa (diğer parmaklar kapalı)
# - VOLUME_DOWN: serçe parmak (pinky) tek başına yukarıdaysa
# - PAUSE: index + middle birlikte yukarı
# - PLAY: başparmak dik ve diğerleri kapalı
# - FORWARD/REWIND: başparmak yana doğru ve diğer parmaklar kapalı
# - FULLSCREEN: Tüm parmaklar açık
# - EXIT_FULLSCREEN: tüm parmaklar kapalı
FINGER_TIPS = [4, 8, 12, 16, 20]
FINGER_PIPS = [2, 6, 10, 14, 18]

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils


def fingers_up(hand_landmarks, y_threshold=0.01):
    lm = hand_landmarks.landmark
    h = []

    h.append(lm[FINGER_TIPS[0]].y < lm[FINGER_PIPS[0]].y - y_threshold)
    for tip, pip in zip(FINGER_TIPS[1:], FINGER_PIPS[1:]):
        h.append(lm[tip].y < lm[pip].y - y_threshold)

    return h


def is_thumb_vertical(hand, thresh_x=0.12, thresh_y=0.008):
    tip = hand.landmark[FINGER_TIPS[0]]
    pip = hand.landmark[FINGER_PIPS[0]]
    dy = pip.y - tip.y
    dx = abs(tip.x - pip.x)
    return (dy > thresh_y) and (dx < thresh_x)

def other_fingers_folded(hand, threshold=0.02):
    for tip_idx, pip_idx in zip(FINGER_TIPS[1:], FINGER_PIPS[1:]):
        tip = hand.landmark[tip_idx]
        pip = hand.landmark[pip_idx]
        if tip.y <= pip.y + threshold:
            return False
    return True


def thumb_lateral_direction(hand, threshold=0.02):
    thumb = hand.landmark[FINGER_TIPS[0]]
    others_tip_idxes = [8, 12, 16, 20]
    others = [hand.landmark[i] for i in others_tip_idxes]
    mean_x = sum(p.x for p in others) / len(others)
    dx = thumb.x - mean_x
    t = max(threshold, 0.02)
    if dx > t:
        return 'RIGHT'
    if dx < -t:
        return 'LEFT'
    return None


class GestureDetector:
    def __init__(self):
        self.last_action_time = 0
        self.last_action = None
        self.cooldown = 2
        self.action_cooldowns = {
            'VOLUME_UP': 0.4,
            'VOLUME_DOWN': 0.4,
            'FORWARD': 0.4,
            'REWIND': 0.4,
        }
        self.last_action_times = {}

        self.active = False
        self.activation_time = 0
        self.activation_delay = 1.5

        self.last_movement_time = 0
        self.deactivation_timeout = 3.0

        self.last_seen = 0
        self.hand_timeout = 2.0
        self.last_volume_time = 0

    def update(self):
        self.last_seen = time.time()

    def detect_activation(self, ups, hand=None):
        others_closed = not any(ups[2:])
        index_up = ups[1]
        thumb_up = ups[0]

        if hand is not None:
            return index_up and is_thumb_vertical(hand) and others_closed

        return thumb_up and index_up and others_closed

    def can_fire(self, action=None):
        quick_actions = {'PAUSE'}

        if action not in quick_actions:
            if not self.active:
                return False
            if (time.time() - self.activation_time) < self.activation_delay:
                return False

        cd = self.action_cooldowns.get(action, self.cooldown)
        last = self.last_action_times.get(action, 0)
        return (time.time() - last) > cd

    def fire(self, action):
        if not self.can_fire(action):
            return False

        now = time.time()
        self.last_action_time = now
        self.last_action = action
        self.last_movement_time = now
        self.last_action_times[action] = now

        if action in ('VOLUME_UP', 'VOLUME_DOWN'):
            self.last_volume_time = now

        print(action)
        return True


detector = GestureDetector()

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Camera could not be opened")
else:
    with mp_hands.Hands(
        max_num_hands=1,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.6
    ) as hands:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb)

            if results.multi_hand_landmarks:
                detector.last_seen = time.time()

                hand = results.multi_hand_landmarks[0]
                mp_drawing.draw_landmarks(frame, hand, mp_hands.HAND_CONNECTIONS)

                ups = fingers_up(hand)

                cv2.putText(frame, f"ups:{ups}", (10, 90),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                cv2.putText(frame, f"Last:{detector.last_action}", (10, 120),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 0), 2)

                if detector.detect_activation(ups, hand) and not detector.active:
                    detector.active = True
                    detector.activation_time = time.time()
                    detector.last_action = None
                    detector.last_movement_time = time.time()

                if detector.active:
                    if time.time() - detector.last_movement_time > detector.deactivation_timeout:
                        detector.active = False

                if detector.active:

                    thumb_dir = thumb_lateral_direction(hand)
                    thumb_vertical = is_thumb_vertical(hand)

                    if not any(ups[1:]) and other_fingers_folded(hand) and not thumb_vertical and thumb_dir == 'RIGHT' and detector.can_fire('REWIND'):
                        detector.fire('REWIND')
                    elif not any(ups[1:]) and other_fingers_folded(hand) and not thumb_vertical and thumb_dir == 'LEFT' and detector.can_fire('FORWARD'):
                        detector.fire('FORWARD')
                    elif ups == [True, False, False, False, False] and thumb_vertical and detector.can_fire('PLAY'):
                        detector.fire('PLAY')
                    elif all(ups[i] for i in [1,2,3,4]) and detector.can_fire('FULLSCREEN'):
                        detector.fire('FULLSCREEN')

                    elif not any(ups) and detector.can_fire('EXIT_FULLSCREEN'):
                        detector.fire('EXIT_FULLSCREEN')
                    elif ups[1] and ups[2] and not ups[2:] and not ups[0] and detector.can_fire('PAUSE'):
                        detector.fire('PAUSE')
                    elif ups == [False, True, False, False, False] and detector.can_fire('VOLUME_UP'):
                        detector.fire('VOLUME_UP')
                    elif ups == [False, False, False, False, True] and detector.can_fire('VOLUME_DOWN'):
                        detector.fire('VOLUME_DOWN')

            else:
                if time.time() - detector.last_seen > detector.hand_timeout:
                    detector.active = False

            status_text = "ACTIVE" if detector.active else "INACTIVE"
            cv2.putText(frame, f"Status: {status_text}", (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                        (0, 255, 0) if detector.active else (0, 0, 255), 2)

            cv2.putText(frame, "Press Q to Quit", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,0), 2)

            cv2.imshow("Youtube controller", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cap.release()
    cv2.destroyAllWindows()