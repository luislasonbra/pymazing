"""Game main loop management (event handling, logic/physics updating and rendering)."""
# Copyright © 2014 Mikko Ronkainen <firstname@mikkoronkainen.com>
# License: MIT, see the LICENSE file.

import time
import distutils.util as du

import sfml as sf
import OpenGL.GL as gl

from pymazing import fps_counter


class GameEngine:
    def __init__(self, window, framebuffer, config):
        self.window = window
        self.framebuffer = framebuffer
        self.framebuffer_scale = float(config["window"]["framebuffer_scale"])
        self.update_frequency = float(config["game"]["update_frequency"])
        self.show_fps = du.strtobool(config["game"]["show_fps"])

        self.should_run = True
        self.game_states = []
        self.active_game_state = None

        self.mouse_previous_position = sf.Vector2()
        self.calculate_mouse_delta()
        self.mouse_delta = sf.Vector2()

        self.fps_counter = fps_counter.FpsCounter()
        self.fps_font = sf.Font.from_file("data/fonts/dejavu-sans-mono-bold.ttf")
        self.fps_text = sf.Text("56", self.fps_font, 16)
        self.fps_text.position = (4, 2)
        self.fps_text.style = sf.Text.REGULAR
        self.fps_text.color = sf.Color(255, 255, 255, 255)

    def run(self):
        """
        The main game loop.

        Details: http://gafferongames.com/game-physics/fix-your-timestep/
        """
        time_step = 1.0 / self.update_frequency
        previous_time = time.clock()
        time_accumulator = 0.0

        # make sure that at least one update happens before rendering
        for game_state in self.game_states:
            game_state.camera.update_projection_matrix(self.framebuffer.width / self.framebuffer.height)
            game_state.update(time_step, self.mouse_delta)

        while self.should_run:
            current_time = time.clock()
            frame_time = current_time - previous_time
            previous_time = current_time

            if frame_time > 0.25:
                frame_time = 0.25

            time_accumulator += frame_time

            while time_accumulator >= time_step:
                self.update(time_step)
                time_accumulator -= time_step

            self.render(time_accumulator / time_step)

    def update(self, time_step):
        """
        Update physics etc. a fixed number of times per second.

        :param float time_step: Time since the last update.
        """
        self.handle_events()
        self.calculate_mouse_delta()
        self.active_game_state.update(time_step, self.mouse_delta)

    def render(self, interpolation):
        """
        Render everything (no fixed time step).

        :param float interpolation: Interpolation value between the fixed physics update steps.
        """
        self.active_game_state.render(self.framebuffer, interpolation)
        self.window.clear(sf.Color.RED)
        self.framebuffer.render()

        if self.show_fps:
            self.fps_text.string = self.fps_counter.get_fps()
            self.window.push_GL_states()
            self.window.draw(self.fps_text)
            self.window.pop_GL_states()

        self.window.display()
        self.framebuffer.clear()
        self.fps_counter.tick()

    def calculate_mouse_delta(self):
        """
        Calculate the mouse movement amount from the previous position.
        """
        self.mouse_delta = self.mouse_previous_position - sf.Mouse.get_position()
        sf.Mouse.set_position(self.window.size / 2, self.window)
        self.mouse_previous_position = sf.Mouse.get_position()

    def update_cameras(self):
        """
        Update camera projection matrices.
        """
        for game_state in self.game_states:
            game_state.camera.update_projection_matrix(self.framebuffer.width / self.framebuffer.height)

    def handle_events(self):
        """
        Handle all events related to the os and the window.
        """
        for event in self.window.events:
            if type(event) is sf.CloseEvent:
                self.should_run = False

            if type(event) is sf.ResizeEvent:
                gl.glViewport(0, 0, event.size.x, event.size.y)
                self.framebuffer.resize(int(self.window.size.x * self.framebuffer_scale + 0.5), int(self.window.size.y * self.framebuffer_scale + 0.5))
                self.update_cameras()

            if type(event) is sf.KeyEvent and event.pressed:
                if event.code == sf.Keyboard.ESCAPE:
                    self.should_run = False

                if event.code == sf.Keyboard.F12:
                    self.framebuffer_scale *= 2.0

                    if self.framebuffer_scale > 1.0:
                        self.framebuffer_scale = 1.0

                    self.framebuffer.resize(int(self.window.size.x * self.framebuffer_scale + 0.5), int(self.window.size.y * self.framebuffer_scale + 0.5))
                    self.update_cameras()

                if event.code == sf.Keyboard.F11:
                    self.framebuffer_scale *= 0.5

                    if self.framebuffer_scale < 0.01:
                        self.framebuffer_scale = 0.01

                    self.framebuffer.resize(int(self.window.size.x * self.framebuffer_scale + 0.5), int(self.window.size.y * self.framebuffer_scale + 0.5))
                    self.update_cameras()

                if event.code == sf.Keyboard.F10:
                    self.framebuffer.set_smoothing(not self.framebuffer.use_smoothing)

                if event.code == sf.Keyboard.F9:
                    self.show_fps = not self.show_fps
