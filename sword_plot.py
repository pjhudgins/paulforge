
import csv
import numpy as np
import matplotlib.pyplot as plt
from pprint import pp

# plt.figure(figsize=(14,10))
MAX_X = 1400
MAX_Y = 1000
CROSSGUARD_X = 1000
SWORD_MAP_CENTER = 150
SWORD_MAP_MAX_Y = 250
MASS_MODEL_CENTER = SWORD_MAP_CENTER + 100
SECOND_IMAGE_SHIFT = 200
SECOND_IMAGE_CENTER = SWORD_MAP_CENTER + SECOND_IMAGE_SHIFT
origin = 0


def parse_cell(cell):
    cell_elements = cell.strip().split("_")
    entry = {}
    for element in cell_elements:
        if not element:
            continue
        identifier = element[0]
        if identifier not in "yczfb":
            raise Exception("Elements must start with y,c,z,f,b, was: "+identifier)
        if identifier in "yc":
            number = int(element[1:])
        else:
            number = float(element[1:])
        entry[identifier] = number

    # for identifier in "yz":
    #     if identifier not in entry:
    #         raise Exception("y and z values are required")

    for identifier in "yczfb":
        if identifier not in entry:
            entry[identifier] = None
    return entry

def read_csv(filename):
    lines = []
    bevels = []
    with open(filename) as csvfile:
        reader = csv.reader(csvfile)#, quoting=csv.QUOTE_NONNUMERIC) # change contents to floats
        for read_row in reader: # each row is a list
            lines.append(read_row)

        pommel_m = int(lines[0][1])
        pommel_x = int(lines[0][2])


        xs = [0]
        for i, cell in enumerate(lines[1][1:]):
            try:
                xs.append(int(cell))
            except:
                break
        num_columns = len(xs) # Includes the all-zeros point where the headers were

        for i in range(2,len(lines), 1):
            row = lines[i]
            if not row:
                break
            if row[0].startswith("#"):
                continue
            # z_row = lines[i+1]
            # if not z_row:
            #     break
            ys = [0]
            y_curves = [None]
            zs = [0.0]
            z_curves = [None]
            z_bulges = [None]  # Z bulge between this point and the previous Y

            for cell in row[1:num_columns]:
                entry = parse_cell(cell)
                if entry['f']:
                    entry['f'] = -entry['f'] #TODO make it clearer that this is negative, or move it elsewhere
                ys.append(entry['y'])
                y_curves.append(entry['c'])
                zs.append(entry['z'])
                z_curves.append(entry['f'])
                z_bulges.append(entry['b'])

            #     try:
            #         ys.append(int(split_cell[0]))
            #     except (IndexError, ValueError):
            #         ys.append(None)
            #     try:
            #         y_curves.append(int(split_cell[1]))
            #     except (IndexError, ValueError):
            #         y_curves.append(None)
            #
            # for cell in z_row[1:num_columns]:
            #     split_cell = cell.split("c")
            #     try:
            #         zs.append(float(split_cell[0]))
            #     except (IndexError, ValueError):
            #         zs.append(None)
            #     try:
            #         z_curves.append(float(split_cell[1]))
            #     except (IndexError, ValueError):
            #         z_curves.append(None)

            bevels.append({"xs": np.array(xs),
                           "ys": np.array(ys),
                           "y_curves": y_curves,
                           "zs": np.array(zs),
                           "z_curves": z_curves,
                           "z_bulges": z_bulges})
        bevels.reverse() # TODO this reverse can be eliminated by fixing the order of xs and ys in line semgents
        model = {"pommel_m": pommel_m,
                 "pommel_x": pommel_x,
                 "bevels": bevels}
    return model


def interpolate(x012, y0_2):
    m = (y0_2[2] - y0_2[0]) / (x012[2] - x012[0])
    b = y0_2[0] - (m * x012[0])
    return m * x012[1] + b


def fill_missing(bevels):
    for i, bevel in enumerate(bevels):
        for key in ["ys", "zs","z_curves"]:
            row = bevel[key]
            for j, val in enumerate(row):
                if bevel[key][j] is None:
                    # for k in range(1,len(bevel)-j): # k>1 is for multiple consecutive nulls
                    for j2 in range(j+1, len(bevel["xs"])):
                        try:
                            xs = [bevel["xs"][j-1], bevel["xs"][j], bevel["xs"][j2]]
                            ys = [bevel[key][j-1],None,bevel[key][j2]]
                            bevel[key][j] = interpolate(xs,ys)
                            break
                        except TypeError as e:  # If multiple Nones in a row, interpolate from the end
                            # print(key,xs,ys,e)
                            pass

                if bevel[key][j] is None: # If no remaining values, just keep filling in previous value
                    bevel[key][j] = bevel[key][j-1]

        for j in range(len(bevel["xs"])):  # Set empty z curves to 0.0
            if bevel["z_curves"][j] is None:
                bevel["z_curves"][j] = 0.0
            bevel["z_curves"][j] = bevel["z_curves"][j] / 2.0  # Dividing everything by 2 because z is half of the thickness
            bevel["zs"][j] = bevel["zs"][j] / 2.0


def line_segment(x01, y01):
    if x01[0] == x01[1]:
        return []  # Prevents divide by zero warning
    try:
        m = (y01[1] - y01[0]) / (x01[1] - x01[0])
        b = y01[0] - (m * x01[0])
    except Exception as e:
        print("x01, y01:", x01, y01)
        raise e
    if x01[0] < x01[1]:
        x = np.arange(x01[0],x01[1],1)
    else:
        x = np.arange(x01[0], x01[1], -1)
    y = m * x + b
    return y


def three_point_arc(x012, y012, sign):
    if x012[0] == x012[2]:
        return []  # Prevents divide by zero warning
    if x012[0] < x012[2]:
        xs = np.arange(x012[0],x012[2],1)
    else:
        xs = np.arange(x012[0], x012[2], -1)

    x1, y1, z1 = x012[0]+(y012[0]*1j), x012[1]+(y012[1]*1j), x012[2]+(y012[2]*1j)
    #print(x1, y1, z1)
    w = z1-x1
    w /= y1-x1
    c = (x1-y1)*(w-abs(w)**2)/2j/w.imag-x1
    #print('(x%+.3f)^2+(y%+.3f)^2 = %.3f^2' % (c.real, c.imag, abs(c+x1)))

    cx = -c.real
    cy = -c.imag
    r = abs(c+x1)
    #print(cx, cy, r)

    ys = cy + sign * np.sqrt(r ** 2 - (xs - cx) ** 2)
    return ys


def bevel_segments(bevel, key, curve_key):
    segments = []
    for j in range(1, len(bevel['xs'])):
        x0 = bevel['xs'][j-1]
        x2 = bevel['xs'][j]
        key0 = bevel[key][j-1]
        key2 = bevel[key][j]
        #print("bevel", bevel)
        curve = None
        if curve_key: #TODO make this less convoluted
            curve = bevel[curve_key][j]
        if curve:
            mid_x = (x0 + x2)/2
            mid_key = ((key0 + key2)/2) + curve
            sign = np.sign(curve)
            segment = three_point_arc([x0, mid_x, x2], [key0, mid_key, key2], sign)
        else:
            segment = line_segment([x0, x2], [key0, key2])
        segments.append(segment)
    return np.concatenate(segments)


def map_plot(model, display_map):
    bevels = model["bevels"]
    blade_length = round(bevels[0]['xs'][-1])
    x_shift = CROSSGUARD_X - blade_length # Shift to align crossguards
    x_range = np.arange(0, blade_length, 1)
    bevel_plots = []

    sword_map = np.full([MAX_X,SWORD_MAP_MAX_Y], 0.0)
    for b, bevel in enumerate(bevels):
        y_segs = bevel_segments(bevels[b], "ys", "y_curves")
        bevel_plots.append(np.concatenate((np.zeros(x_shift), y_segs)))
        #TODO move some of these to analysis
        plt.plot(x_range + x_shift, origin + SWORD_MAP_CENTER - y_segs, color='black', linewidth=1) # Inverting y values
        plt.plot(x_range + x_shift, origin + SECOND_IMAGE_CENTER - y_segs, ":", color='black', linewidth=.2)  # Inverting y values
        # plt.plot(bevels[b]["xs"] + x_shift, origin + SECOND_IMAGE_CENTER - bevels[b]["ys"], ".", color='blue', markersize=2)

        if b > 0:
            prev_y_segs = bevel_segments(bevels[b-1], "ys", "y_curves")
            z_segs = bevel_segments(bevels[b], "zs", None)
            prev_z_segs = bevel_segments(bevels[b-1], "zs", None)
            z_curve_segs = bevel_segments(bevels[b], 'z_curves', None)
            for xi in x_range:
                # # Note: Inverting y values here from edge-high to edge-low
                # y0 = origin - round(prev_y_segs[xi])
                # y1 = origin - round(y_segs[xi])
                y0 = SWORD_MAP_CENTER - round(prev_y_segs[xi])
                y1 = SWORD_MAP_CENTER - round(y_segs[xi])
                y_mid = (y0 + y1) / 2
                z0 = prev_z_segs[xi]
                z1 = z_segs[xi]
                curve = z_curve_segs[xi]
                z_mid = ((z0 + z1) / 2) + curve
                if curve:
                    sword_map[xi][y0:y1] = three_point_arc([y0, y_mid, y1], [z0, z_mid, z1], np.sign(curve))
                else:
                    sword_map[xi][y0:y1] = line_segment([y0, y1], [z0, z1])

    ## Pommel #TODO this is a hack
    pommel_x = max(x_range) - model["pommel_x"]
    pommel_m = model["pommel_m"]

    for i in range(max(x_range)+1, pommel_x):
        for j in range(140, 160):
            sword_map[i][j] = 2.0

    r = round(5*np.sqrt(pommel_m))  # TODO 5 is a total arbitrary number
    for i in range(pommel_x-r, pommel_x+r):
        # term = (i-pommel_x)**2
        curve = round(np.sqrt(r**2 - (i-pommel_x)**2))
        # for j in range(150 - pommel_m, 150 + pommel_m):
        for j in range(150 - curve, 150 + curve):
            sword_map[i][j] = 4.0


    ## Shifted sword map to align crossguards
    x_shifted_sword_map = np.full([MAX_X, SWORD_MAP_MAX_Y], 0.0)
    for x in range(MAX_X):
        for y in range(SWORD_MAP_MAX_Y):
            if sword_map[x][y] > 0.0:
                adjusted_x = x + x_shift
                if adjusted_x >= MAX_X:
                    raise Exception("Hilt is too long")
                if adjusted_x < 0:
                    raise Exception("Blade is too long")
                x_shifted_sword_map[adjusted_x][y] = sword_map[x][y]

    ## Display map
    for x in range(MAX_X):
        for y in range(SWORD_MAP_MAX_Y):
            if x_shifted_sword_map[x][y] > 0.0:
                shifted_y = y + origin ##+ SWORD_MAP_CENTER

                display_map[x][shifted_y] = x_shifted_sword_map[x][y]

    return x_shifted_sword_map, bevel_plots




