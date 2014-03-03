"""
Transform 3D data to shapes on the screen.

:copyright: © 2014 Mikko Ronkainen <firstname@mikkoronkainen.com>
:license: MIT License, see the LICENSE file.
"""

import numpy as np

from pymazing import color, rasterizer, clipper


def render_world(world, camera, framebuffer, do_backface_culling=True, render_wireframe=False):
    view_space_triangles = []

    for mesh in world.meshes:
        if not camera.frustum.sphere_is_inside(mesh.position, mesh.bounding_radius):
            continue

        mesh.calculate_world_matrix()
        world_matrix = mesh.world_matrix
        view_matrix = camera.view_matrix.dot(world_matrix)

        world_space_vertices = []
        view_space_vertices = []

        for vertex in mesh.vertices:
            world_space_vertices.append(world_matrix.dot(vertex))
            view_space_vertices.append(view_matrix.dot(vertex))

        for i, index in enumerate(mesh.indices):
            v0 = world_space_vertices[index[0]]
            v1 = world_space_vertices[index[1]]
            v2 = world_space_vertices[index[2]]

            triangle_position = v0[:3]

            triangle_normal = np.cross([v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2]], [v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2]])
            triangle_normal /= np.linalg.norm(triangle_normal)

            triangle_to_camera = camera.position - triangle_position
            triangle_to_camera /= np.linalg.norm(triangle_to_camera)

            if do_backface_culling and np.dot(triangle_to_camera, triangle_normal) < 0.0:
                continue

            combined_light_color = np.array([0.0, 0.0, 0.0, 0.0])

            if world.ambient_light_enabled:
                combined_light_color += world.ambient_light.color.get_vector() * world.ambient_light.intensity

            if world.diffuse_lights_enabled:
                for diffuse_light in world.diffuse_lights:
                    triangle_to_light = diffuse_light.position[:3] - triangle_position
                    triangle_to_light /= np.linalg.norm(triangle_to_light)
                    diffuse_amount = np.dot(triangle_to_light, triangle_normal)
                    diffuse_amount = np.clip(diffuse_amount, 0.0, 1.0)
                    combined_light_color += diffuse_light.color.get_vector() * diffuse_light.intensity * diffuse_amount

            if world.specular_lights_enabled:
                for specular_light in world.specular_lights:
                    triangle_to_light = specular_light.position[:3] - triangle_position
                    triangle_to_light /= np.linalg.norm(triangle_to_light)

                    if np.dot(triangle_to_light, triangle_normal) > 0.0:
                        reflection_vector = 2.0 * np.dot(triangle_to_light, triangle_normal) * triangle_normal - triangle_to_light
                        reflection_vector /= np.linalg.norm(reflection_vector)
                        specular_amount = np.dot(triangle_to_camera, reflection_vector)
                        specular_amount = np.clip(specular_amount, 0.0, 1.0)
                        specular_amount = pow(specular_amount, specular_light.shininess)
                        combined_light_color += specular_light.color.get_vector() * specular_light.intensity * specular_amount

            original_triangle_color = mesh.colors[i].get_vector()
            final_triangle_color = original_triangle_color * combined_light_color
            final_triangle_color = np.clip(final_triangle_color, 0.0, 1.0)

            v0 = view_space_vertices[index[0]]
            v1 = view_space_vertices[index[1]]
            v2 = view_space_vertices[index[2]]

            view_space_triangles.append((v0, v1, v2, color.from_vector(final_triangle_color)))

    view_space_triangles_z_clipped = []

    for view_space_triangle in view_space_triangles:
        clipped_triangles = clipper.clip_view_space_triangle_by_z(view_space_triangle, camera.near_z, camera.far_z)

        if clipped_triangles is not None:
            view_space_triangles_z_clipped.extend(clipped_triangles)

    screen_space_triangles_clipped = []

    for view_space_triangle in view_space_triangles_z_clipped:
        v0 = camera.projection_matrix.dot(view_space_triangle[0])
        v1 = camera.projection_matrix.dot(view_space_triangle[1])
        v2 = camera.projection_matrix.dot(view_space_triangle[2])
        color_ = view_space_triangle[3]

        x0 = v0[0] / v0[3] * framebuffer.half_width + framebuffer.half_width
        y0 = v0[1] / v0[3] * framebuffer.half_height + framebuffer.half_height
        z0 = v0[2] / v0[3]

        x1 = v1[0] / v1[3] * framebuffer.half_width + framebuffer.half_width
        y1 = v1[1] / v1[3] * framebuffer.half_height + framebuffer.half_height
        z1 = v1[2] / v1[3]

        x2 = v2[0] / v2[3] * framebuffer.half_width + framebuffer.half_width
        y2 = v2[1] / v2[3] * framebuffer.half_height + framebuffer.half_height
        z2 = v2[2] / v2[3]

        min_z = min(min(z0, z1), z2)
        screen_space_triangle = (np.array([x0, y0, z0]), np.array([x1, y1, z1]), np.array([x2, y2, z2]), color_, min_z)
        clipped_triangles = clipper.clip_screen_space_triangle(screen_space_triangle, framebuffer.width - 1, framebuffer.height - 1)

        if clipped_triangles is not None:
            screen_space_triangles_clipped.extend(clipped_triangles)

    screen_space_triangles_clipped.sort(key=lambda t: t[4], reverse=True)

    for screen_space_triangle in screen_space_triangles_clipped:
        v0 = screen_space_triangle[0]
        v1 = screen_space_triangle[1]
        v2 = screen_space_triangle[2]
        color_ = screen_space_triangle[3]

        x0 = int(v0[0] + 0.5)
        y0 = int(v0[1] + 0.5)
        z0 = v0[2]

        x1 = int(v1[0] + 0.5)
        y1 = int(v1[1] + 0.5)
        z1 = v1[2]

        x2 = int(v2[0] + 0.5)
        y2 = int(v2[1] + 0.5)
        z2 = v2[2]

        if render_wireframe:
            rasterizer.draw_line(framebuffer, x0, y0, x1, y1, color_)
            rasterizer.draw_line(framebuffer, x1, y1, x2, y2, color_)
            rasterizer.draw_line(framebuffer, x2, y2, x0, y0, color_)
        else:
            rasterizer.draw_triangle(framebuffer, x0, y0, x1, y1, x2, y2, color_)

