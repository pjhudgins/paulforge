
import csv
import numpy as np
import matplotlib.pyplot as plt
from pprint import pp
import sword_plot
from sword_plot import *


plt.figure(figsize=(14,10))


def plot_vertical_mark(x, y, color):
    plt.plot(np.full(80, x), np.arange(y-40, y+40), ":", color=color, linewidth=2.0)


def plot_slice(x, sword_map, origin):
    ys = []
    zs = []
    for y in range(SWORD_MAP_MAX_Y):
        if sword_map[x][y] > 0.0:
            ys.append(y)
            zs.append(sword_map[x][y])

    ys = np.array(ys)
    zs = np.array(zs)
    bloat_factor = 1.0  # NOTE bloat factor
    plt.plot(x + bloat_factor * zs, origin + SECOND_IMAGE_SHIFT + ys, color="black", linewidth=0.3) #TODO define y in terms of SECOND_IMAGE_SHIFT & SWORD_MAP_CENTER
    plt.plot(x - bloat_factor * zs, origin + SECOND_IMAGE_SHIFT + ys, color="black", linewidth=0.3)


def analyze(model, sword_map, bevel_plots):
    origin = sword_plot.origin
    mass_distribution = np.zeros(MAX_X)


    for x in range (50, CROSSGUARD_X, 15):
        plot_slice(x,sword_map,origin)

    for i in range(MAX_X):
        for j in range(SWORD_MAP_MAX_Y):
            if sword_map[i][j] > 0.0:
                mass_distribution[i] += sword_map[i][j]

    blade_length = round(model["bevels"][0]['xs'][-1]) #TODO add this and x_shift to object
    x_shift = CROSSGUARD_X - blade_length  # Shift to align  #TODO duplicated in sword_plot
    for bevel in model["bevels"]:
        plt.plot(bevel["xs"] + x_shift, origin + SECOND_IMAGE_CENTER - bevel["ys"], ".", color='blue', markersize=2)
    for x in model["bevels"][0]["xs"]:
        label = f"x: {x}\n  v"
        plt.text(x + x_shift - 10, origin + SECOND_IMAGE_CENTER+40, label, rotation="vertical")


    xs = np.arange(MAX_X)
    plt.plot(xs, np.full(MAX_X, origin+SECOND_IMAGE_CENTER), ":", color='black', linewidth=1)
    plt.plot(xs, mass_distribution/2 + origin, ":", color='black', linewidth=1)
    plt.plot(xs, np.full(MAX_X, origin), color='black', linewidth=1)

    sig_x_d = 0.0
    mass = 0.0
    for x in range(MAX_X):
        sig_x_d += x * mass_distribution[x]
        mass += mass_distribution[x]


    point_of_balance = sum(np.multiply(xs,mass_distribution)) / sum(mass_distribution)
    print("cog", CROSSGUARD_X - point_of_balance)
    plot_vertical_mark(point_of_balance, origin+SECOND_IMAGE_CENTER, 'xkcd:brown')
    # plt.text(500, origin+80, f"pob: \n{round(CROSSGUARD_X-point_of_balance)}")

    moi_elements = np.multiply(np.multiply(mass_distribution, xs-point_of_balance), xs-point_of_balance)
    moment_of_intertia = sum(moi_elements)
    radius_of_gyration = np.sqrt(moment_of_intertia / sum(mass_distribution))
    print("moi/rog", moment_of_intertia, radius_of_gyration)
    # plt.text(700, origin + 80, f"rog: {round(radius_of_gyration)}")

    bar_start = point_of_balance - (radius_of_gyration * np.sqrt(3)) # Based on formula for a radius of gyration of a uniform bar
    bar_end  = point_of_balance + (radius_of_gyration * np.sqrt(3))
    bar = range(round(bar_start), round(bar_end))
    plot_vertical_mark(point_of_balance - radius_of_gyration, origin+SECOND_IMAGE_CENTER, 'xkcd:pink')
    plot_vertical_mark(point_of_balance + radius_of_gyration, origin + SECOND_IMAGE_CENTER, 'xkcd:pink')
    plt.plot(bar, [origin + SECOND_IMAGE_CENTER - 40] * len(bar), color='brown', linewidth=4)

    volume = sum(mass_distribution) / 1000
    # plt.text(900, origin + 80, f"vol: {round(volume)}")

    stats = f"pob: {round(CROSSGUARD_X-point_of_balance)}"
    stats += f"\nrog: {round(radius_of_gyration)}"
    stats += f"\nvol: {round(volume)}"
    plt.text(10, origin+10, stats)

    cross_sectional_com = np.zeros(CROSSGUARD_X)
    y_strength = np.zeros(CROSSGUARD_X)
    z_strength = np.zeros(CROSSGUARD_X)
    edge_robustness = np.zeros(CROSSGUARD_X)

    for x in range(CROSSGUARD_X):
        ys = np.arange(SWORD_MAP_MAX_Y)
        #print("shapes", np.shape(ys), np.shape(sword_map[x]))
        cross_sectional_com[x] = sum(np.multiply(ys, sword_map[x]))/sum(sword_map[x])
        for y in range(SWORD_MAP_MAX_Y):
            distance_from_xcom = abs(y - cross_sectional_com[x])
            thickness = sword_map[x][y]
            y_strength[x] += thickness * distance_from_xcom
            z_strength[x] += (thickness ** 2) / 4 # /2 for integral, *2 for symmetry, /4 for half of thickness sqd

            distance_from_edge = abs(y - bevel_plots[0][x]) #TODO definitely using wrong distance
            edge_robustness[x] += thickness / (distance_from_edge ** 3)
            #print("y/plot/distance/robustness", y, bevel_plots[0][x], distance_from_edge, edge_robustness[x])

    plt.plot(xs[:CROSSGUARD_X], cross_sectional_com + origin + SECOND_IMAGE_SHIFT, color='red', linewidth=.5)
    plt.plot(xs[:CROSSGUARD_X], (y_strength / 10.0) + origin, color='red', linewidth=1)  # Divide by arbitrary scale factor
    plt.plot(xs[:CROSSGUARD_X], (z_strength / 1.0) + origin, color='blue', linewidth=1)
    plt.plot(xs[:CROSSGUARD_X], (edge_robustness * 500000) + origin, color='green', linewidth=1)

    tip = 0  ############## TODO cleanup ############################
    for x in xs:
        if mass_distribution[x] > 0.0:
            tip = x
            break
    relative_y_strength = []
    for x in range(tip,CROSSGUARD_X):
        relative_y_strength.append(100*y_strength[x]/(x-tip))
    plt.plot(xs[tip:CROSSGUARD_X], np.array(relative_y_strength)+origin, color='xkcd:orange', linewidth=1)




# origin = 0
def read_and_plot(fn, map):
    # global sword_plot.origin


    model = read_csv(fn)
    # print(fn, "model:")
    # pp(model)
    fill_missing(model["bevels"])
    print(fn, "filled model:")
    pp(model)

    sword_map, bevel_plots = map_plot(model, map)
    analyze(model, sword_map, bevel_plots)
    sword_plot.origin += 350

import warnings
warnings.filterwarnings("ignore") # TODO narrow this down

max_z = 4  # This has an effect on color gradients.
# tmap = np.full([1400, 1000], float(max_z)) #Thickness map
tmap = np.zeros([1400,1000])

read_and_plot("c15_prince2.csv", tmap)
# read_and_plot("c15_katana.csv", tmap)
# read_and_plot("c15_f3c.csv", tmap)
# read_and_plot("c15_saber_3.csv", tmap)
read_and_plot("c15_saber_5c.csv", tmap)
read_and_plot("c15_saber_5d.csv", tmap)

cmap='terrain'
cmap = 'YlGnBu_r'
cmap = 'hot_r'

plt.imshow(np.transpose(tmap), cmap=cmap, aspect='auto')#, interpolation='nearest')
plt.gca().invert_yaxis()

plt.show()



