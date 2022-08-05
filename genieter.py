from kivymd.app import MDApp
from kivy.properties import BooleanProperty, BoundedNumericProperty, DictProperty, ConfigParserProperty
# from bluedot import BlueDot
from subprocess import DEVNULL, STDOUT, check_call


def configuration_bool(value):
    if isinstance(value, str):
        return value.lower() not in ('false', 'off', 'no', '')
    return bool(value)


class GenieterApp(MDApp):
    lock = BooleanProperty(True)
    volume = BoundedNumericProperty(50, min=0, max=100)
    mute = BooleanProperty(False)

    # Navigation lights
    # noinspection PyArgumentList
    link_board_lights = ConfigParserProperty('On', 'navigation', 'link_board_lights', 'app',
                                             val_type=configuration_bool)
    board_lights = BooleanProperty(False)

    navigation_lights = DictProperty({
        'port': False,
        'starboard': False,
        'masthead': False,
        'stern': False,
    })

    def on_board_lights(self, instance, board_lights):
        if self.link_board_lights:
            self.navigation_lights['port'] = self.navigation_lights['starboard'] = board_lights

            if board_lights:
                self.navigation_lights['masthead'] = True

    # noinspection PyUnusedLocal
    def on_link_board_lights(self, instance, link_board_lights):
        if link_board_lights and (self.navigation_lights['port'] or self.navigation_lights['starboard']):
            self.navigation_lights['starboard'] = self.navigation_lights['port'] = True

        if link_board_lights and self.board_lights:
            self.navigation_lights['masthead'] = True

    ceiling_light = BooleanProperty(False)

    wiper_left = BooleanProperty(False)
    wiper_right = BooleanProperty(False)

    horn = BooleanProperty(False)

    # bd = BlueDot()
    # bd.when_moved = volume

    def on_mute(self, instance, mute):
        check_call(["amixer", "-D", "pulse", "sset", "Master", "off" if self.mute else "on"],
                   stdout=DEVNULL, stderr=STDOUT)

    def on_volume(self, instance, volume):
        check_call(["amixer", "-D", "pulse", "sset", "Master", str(self.volume) + "%"],
                   stdout=DEVNULL, stderr=STDOUT)

    def build(self):
        # Palette colors are:   'Red', 'Pink', 'Purple', 'DeepPurple', 'Indigo', 'Blue',
        #                       'LightBlue', 'Cyan', 'Teal', 'Green', 'LightGreen',
        #                       'Lime', 'Yellow', 'Amber', 'Orange', 'DeepOrange',
        #                       'Brown', 'Gray', 'BlueGray'
        self.theme_cls.primary_palette = "LightBlue"

        # theme_colors are: 'Primary', 'Secondary', 'Background', 'Surface', 'Error',
        #                   'On_Primary', 'On_Secondary', 'On_Background',
        #                   'On_Surface', 'On_Error'
        self.theme_cls.theme_style = "Dark"

    def build_config(self, config):
        config.setdefaults('navigation', {
            'link_board_lights': 'On',
        })


GenieterApp().run()
