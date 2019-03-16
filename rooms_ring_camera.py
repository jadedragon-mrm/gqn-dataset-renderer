import argparse
import colorsys
import math
import os
import random
import time

import cv2
import matplotlib.pyplot as plt
import numpy as np
import pyglet
import trimesh
from PIL import Image, ImageEnhance
from tqdm import tqdm

from OpenGL.GL import GL_LINEAR_MIPMAP_LINEAR

from archiver import Archiver, SceneData
from pyrender import (DirectionalLight, Mesh, Node, OffscreenRenderer,
                      PerspectiveCamera, PointLight, RenderFlags, Scene,
                      Primitive)



def set_random_texture(node, path, intensity=1.0):
    texture_image = Image.open(path)
    if intensity < 1.0:
        enhancer = ImageEnhance.Brightness(texture_image)
        texture_image = enhancer.enhance(intensity)
    primitive = node.mesh.primitives[0]
    assert isinstance(primitive, Primitive)
    primitive.material.baseColorTexture.source = texture_image
    primitive.material.baseColorTexture.sampler.minFilter = GL_LINEAR_MIPMAP_LINEAR


def build_scene(colors, floor_textures, wall_textures, objects):
    scene = Scene(
        bg_color=np.array([153 / 255, 226 / 255, 249 / 255]),
        ambient_light=np.array([0.5, 0.5, 0.5, 1.0]))

    floor_trimesh = trimesh.load("objects/floor.obj")
    mesh = Mesh.from_trimesh(floor_trimesh)
    node = Node(
        mesh=mesh,
        rotation=generate_quaternion(pitch=-math.pi / 2),
        translation=np.array([0, 0, 0]))
    texture_path = random.choice(floor_textures)
    set_random_texture(node, texture_path, intensity=0.8)
    scene.add_node(node)

    texture_path = random.choice(wall_textures)

    wall_trimesh = trimesh.load("objects/wall.obj")
    mesh = Mesh.from_trimesh(wall_trimesh)
    node = Node(mesh=mesh, translation=np.array([0, 1.15, -3.5]))
    set_random_texture(node, texture_path)
    scene.add_node(node)

    mesh = Mesh.from_trimesh(wall_trimesh)
    node = Node(
        mesh=mesh,
        rotation=generate_quaternion(yaw=math.pi),
        translation=np.array([0, 1.15, 3.5]))
    set_random_texture(node, texture_path)
    scene.add_node(node)

    mesh = Mesh.from_trimesh(wall_trimesh)
    node = Node(
        mesh=mesh,
        rotation=generate_quaternion(yaw=-math.pi / 2),
        translation=np.array([3.5, 1.15, 0]))
    set_random_texture(node, texture_path)
    scene.add_node(node)

    mesh = Mesh.from_trimesh(wall_trimesh)
    node = Node(
        mesh=mesh,
        rotation=generate_quaternion(yaw=math.pi / 2),
        translation=np.array([-3.5, 1.15, 0]))
    set_random_texture(node, texture_path)
    scene.add_node(node)

    # light = PointLight(color=np.ones(3), intensity=200.0)
    # node = Node(
    #     light=light,
    #     translation=np.array([0, 5, 5]))
    # scene.add_node(node)

    light = DirectionalLight(color=np.ones(3), intensity=10)
    position = np.array([0, 1, 1])
    position = position / np.linalg.norm(position)
    yaw, pitch = compute_yaw_and_pitch(position, 1)
    node = Node(
        light=light,
        rotation=genearte_camera_quaternion(yaw, pitch),
        translation=np.array([0, 1, 1]))
    scene.add_node(node)

    # Place objects
    node = random.choice(objects)
    node.mesh.primitives[0].color_0 = (255, 0, 255, 255)
    parent = Node(children=[node], translation=np.array([0, 0, -1]))
    scene.add_node(parent)

    return scene


def udpate_vertex_buffer(cube_nodes):
    for node in (cube_nodes):
        node.mesh.primitives[0].update_vertex_buffer_data()



def compute_yaw_and_pitch(position, distance):
    x, y, z = position
    if z < 0:
        yaw = math.pi + math.atan(x / z)
    elif x < 0:
        yaw = math.pi * 2 + math.atan(x / z)
    else:
        yaw = math.atan(x / z)
    pitch = -math.asin(y / distance)
    return yaw, pitch


def genearte_camera_quaternion(yaw, pitch):
    quaternion_yaw = generate_quaternion(yaw=yaw)
    quaternion_pitch = generate_quaternion(pitch=pitch)
    quaternion = multiply_quaternion(quaternion_pitch, quaternion_yaw)
    quaternion = quaternion / np.linalg.norm(quaternion)
    return quaternion


def main():
    try:
        os.makedirs(args.output_directory)
    except:
        pass

    # Colors
    colors = []
    for n in range(args.num_colors):
        hue = n / args.num_colors
        saturation = 1
        lightness = 1
        red, green, blue = colorsys.hsv_to_rgb(hue, saturation, lightness)
        colors.append(np.array((red, green, blue)))

    floor_textures = [
        "textures/lg_floor_d.tga",
        "textures/lg_style_01_floor_blue_d.tga",
        "textures/lg_style_01_floor_orange_bright_d.tga",
    ]

    wall_textures = [
        "textures/lg_style_01_wall_cerise_d.tga",
        "textures/lg_style_01_wall_green_bright_d.tga",
        "textures/lg_style_01_wall_red_bright_d.tga",
        "textures/lg_style_02_wall_yellow_d.tga",
        "textures/lg_style_03_wall_orange_bright_d.tga",
    ]

    objects = [
        # get_sphere_node(),
        get_capsule_node(),
        # get_cylinder_node(),
    ]

    scene = build_scene(colors, floor_textures, wall_textures, objects)
    camera = PerspectiveCamera(yfov=math.pi / 4)
    camera_node = Node(camera=camera, translation=np.array([0, 1, 1]))
    scene.add_node(camera_node)
    renderer = OffscreenRenderer(
        viewport_width=args.image_size, viewport_height=args.image_size)

    for m in range(100):
        rand_position_xz = np.random.uniform(-3, 3, size=2)
        rand_position_xz = 3 * rand_position_xz / np.linalg.norm(
            rand_position_xz)
        rand_lookat_xz = np.random.uniform(-6, 6, size=2)
        rand_lookat_xz = np.array([0, 0])
        camera_position = np.array(
            [rand_position_xz[0], 1, rand_position_xz[1]])
        eye_direction = rand_position_xz - rand_lookat_xz
        eye_direction = np.array([eye_direction[0], 0, eye_direction[1]])
        # Compute yaw and pitch
        yaw, pitch = compute_yaw_and_pitch(eye_direction,
                                           np.linalg.norm(eye_direction))

        camera_node.rotation = genearte_camera_quaternion(yaw, pitch)
        camera_node.translation = camera_position

        print(camera_position, yaw, pitch)

        # v = Viewer(scene, shadows=True, viewport_size=(400, 400))

        # Rendering
        flags = RenderFlags.SHADOWS_DIRECTIONAL
        if args.anti_aliasing:
            flags |= RenderFlags.ANTI_ALIASING
        image = renderer.render(scene, flags=flags)[0]
        plt.clf()
        plt.imshow(image)
        plt.pause(1)

    renderer.delete()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--total-scenes", "-total", type=int, default=2000000)
    parser.add_argument("--num-scenes-per-file", type=int, default=2000)
    parser.add_argument("--initial-file-number", type=int, default=1)
    parser.add_argument("--num-observations-per-scene", type=int, default=15)
    parser.add_argument("--image-size", type=int, default=64)
    parser.add_argument("--num-cubes", type=int, default=5)
    parser.add_argument("--num-colors", type=int, default=10)
    parser.add_argument("--output-directory", type=str, required=True)
    parser.add_argument("--anti-aliasing", default=False, action="store_true")
    args = parser.parse_args()
    main()
