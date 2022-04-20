import cv2
from airtest.core.cv import Template
import airtest.core.api as airtest
import logging

logging.basicConfig()
logging.getLogger("airtest").setLevel(logging.WARNING)
logger = logging.getLogger('eve-monitor')

HOSTILE = 'hostile'
NEUTRAL = 'neutral'
FRIENDLY = 'friendly'

LOCAL_PLAYER_TOP_OFFSET = 500
EMPTY_POSITION_IN_CHAT = (120, 100)

SCREENSHOT_DIR = 'tmp'
RESOURCE_DIR = 'resource'


def report(local_standings):
    # When this method is called, the chat/character window is still open.
    if len(local_standings[HOSTILE]) + len(local_standings[NEUTRAL]) == 0:
        airtest.touch(EMPTY_POSITION_IN_CHAT)
        airtest.sleep(1)  # Wait for screen to move into position.
        airtest.touch((150, 1050))
        airtest.text("Clear")
    else:
        for x, y in local_standings[HOSTILE]:
            airtest.touch((x, y + LOCAL_PLAYER_TOP_OFFSET))

        for x, y in local_standings[NEUTRAL]:
            airtest.touch((x, y + LOCAL_PLAYER_TOP_OFFSET))

        airtest.touch(Template(f"{RESOURCE_DIR}/location_tab.png", threshold=0.92, resolution=(1440, 1080)))
        airtest.touch((400, 600))  # current system

    airtest.touch(EMPTY_POSITION_IN_CHAT)
    airtest.touch(Template(f"{RESOURCE_DIR}/corp_chat.png", threshold=0.78, resolution=(1440, 1080)))
    airtest.sleep(1)  # Wait for chat tab to switch.
    airtest.touch(Template(f"{RESOURCE_DIR}/send_button.png", threshold=0.92, resolution=(1440, 1080)))


def close_chat():
    airtest.touch(EMPTY_POSITION_IN_CHAT)
    airtest.touch(Template(f"{RESOURCE_DIR}/close_button.png", threshold=0.92, resolution=(1440, 1080)))


def report_discord(discord_client, local_standings):
    hostile_count = len(local_standings[HOSTILE])
    neutral_count = len(local_standings[NEUTRAL])

    if hostile_count + neutral_count == 0:
        discord_client.send_message('Clear')
    else:
        message = f'Hostile: {hostile_count}, Neutral: {neutral_count}'
        discord_client.send_message(message, image=f'{SCREENSHOT_DIR}/screen_local.png')


def open_chat_local():
    airtest.touch((300, 1000))
    airtest.touch(Template(f"{RESOURCE_DIR}/menu.png", threshold=0.92, resolution=(1440, 1080)))
    airtest.touch(Template(f"{RESOURCE_DIR}/character_tab.png", threshold=0.92, resolution=(1440, 1080)))
    airtest.sleep(1)


def get_local_overview():
    screenshot_file_name = f'{SCREENSHOT_DIR}/screen_overview.png'
    airtest.snapshot(screenshot_file_name)
    screen = cv2.imread(screenshot_file_name, cv2.IMREAD_UNCHANGED)

    local_tab_up = Template(f"{RESOURCE_DIR}/local_overview_top.png", threshold=0.88, resolution=(1440, 1080)).match_all_in(screen)
    local_tab_bottom = Template(f"{RESOURCE_DIR}/local_overview_bottom.png", threshold=0.92, resolution=(1440, 1080)).match_all_in(screen)

    if local_tab_up and local_tab_bottom:
        (_, (local_tab_left_line, local_tab_top_line), (local_tab_right_line, _), _) = local_tab_up[0].get('rectangle')
        ((_, local_tab_bottom_line), _, _, _) = local_tab_bottom[0].get('rectangle')

        return screen[local_tab_top_line: local_tab_bottom_line, local_tab_left_line:local_tab_right_line]
    else:
        return None


def identify_standing(name_image):
    h, w = name_image.shape[:2]
    standing = None

    # Resolve wrong match_all_in for blank image.
    if is_blank_name_row(name_image):
        standing = None
    # order by possibility to improve efficiency
    elif (Template(f"{RESOURCE_DIR}/blue_plus.png", threshold=0.88, resolution=(w, h)).match_all_in(name_image) is not None or
          # matching on gray scale image. blue_star image works for green_star as well.
          Template(f"{RESOURCE_DIR}/blue_star.png", threshold=0.88, resolution=(w, h)).match_all_in(name_image) is not None):
        standing = FRIENDLY
    elif Template(f"{RESOURCE_DIR}/red_mark.png", threshold=0.82, resolution=(w, h)).match_all_in(name_image) is not None:
        standing = HOSTILE
    elif not (Template(f"{RESOURCE_DIR}/observer.png", threshold=0.92, resolution=(w, h)).match_in(name_image) or
              Template(f"{RESOURCE_DIR}/observer_name.png", threshold=0.90, resolution=(w, h)).match_in(name_image)):
        standing = NEUTRAL

    logger.debug(f'standing: {standing}')
    if logger.level <= logging.DEBUG:
        results = Template(f"{RESOURCE_DIR}/observer_name.png", threshold=0.80, resolution=(w, h)).match_all_in(name_image)
        logger.debug(results)
        show_image(name_image)

    return standing


def is_blank_name_row(name_row):
    _, name_row_bin = cv2.threshold(cv2.cvtColor(name_row, cv2.COLOR_BGR2GRAY), 100, 255, cv2.THRESH_BINARY)

    return cv2.countNonZero(name_row_bin) == 0


def identify_local_in_overview():
    local_overview = get_local_overview()

    if local_overview is None:
        logger.warning('Local overview not available')
        return None
    else:
        h, w = local_overview.shape[:2]  # cv image are h x w
        divider_template = Template(f"{RESOURCE_DIR}/divider.png", threshold=0.76, resolution=(w, h))

        dividers = divider_template.match_all_in(local_overview)

        if dividers is None:
            divider_positions = []
        else:
            divider_positions = list(map(lambda divider: divider.get('result')[1], dividers))
        divider_positions.sort()
        divider_positions.append(h)

        prev_position = 0

        friendly_count = 0
        hostile_count = 0
        neutral_count = 0
        for current_position in divider_positions:
            if current_position - prev_position > 40:
                name_row = local_overview[prev_position:current_position, :]
                standing = identify_standing(name_row)

                if HOSTILE == standing:
                    hostile_count += 1
                elif NEUTRAL == standing:
                    neutral_count += 1
                elif FRIENDLY == standing:
                    friendly_count += 1

                prev_position = current_position

    logger.debug(f'hostile_count: {hostile_count}; neutral_count: {neutral_count}; friendly_count: {friendly_count}')
    return {HOSTILE: hostile_count, NEUTRAL: neutral_count, FRIENDLY: friendly_count}


def identify_local_in_chat():
    open_chat_local()

    screenshot_file_name = f'{SCREENSHOT_DIR}/screen_chat.png'
    airtest.snapshot(screenshot_file_name)
    screen = cv2.imread(screenshot_file_name, cv2.IMREAD_UNCHANGED)

    local_bottom = 900

    local = screen[LOCAL_PLAYER_TOP_OFFSET:local_bottom, :]
    cv2.imwrite(f'{SCREENSHOT_DIR}/screen_local.png', local)

    # (25, 580); (300, 670);
    # distance: 103: 683, 786
    # distance: 325: 350, 675, 1000, 1325

    screen_h, screen_w = screen.shape[:2]

    h = 90
    w = 275

    x_origin = 25
    y_origin = 580 - LOCAL_PLAYER_TOP_OFFSET
    x_distance = 325
    y_distance = 103
    current_x = x_origin

    local_standings = {FRIENDLY: [], HOSTILE: [], NEUTRAL: []}

    found_blank = False
    while current_x < screen_w and not found_blank:
        for pos in range(3):
            current_y = y_origin + pos * y_distance
            lower_bound = current_y + h
            right_bound = min(current_x + w, screen_w)
            name = local[current_y:lower_bound, current_x:right_bound]

            standing = identify_standing(name)
            if standing is not None:
                local_standings[standing].append((int((current_x + right_bound) / 2), int((current_y + lower_bound) / 2)))

            if is_blank_name_row(name):
                found_blank = True
                break

        current_x += x_distance

    return local_standings


def show_image(image):
    cv2.imshow('any', image)
    cv2.waitKey()


def initialize_device():
    # android://127.0.0.1:5037/emulator-5554?cap_method=MINICAP&&ori_method=MINICAPORI&&touch_method=MINITOUCH
    # android://127.0.0.1:5037/127.0.0.1:7555?cap_method=JAVACAP&&ori_method=MINICAPORI&&touch_method=MINITOUCH
    airtest.auto_setup(__file__, devices=[
        "android://127.0.0.1:5037/emulator-5554?cap_method=MINICAP&&ori_method=MINICAPORI&&touch_method=MINITOUCH"])
