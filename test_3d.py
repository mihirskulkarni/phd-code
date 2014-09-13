from scipy.spatial import Voronoi
import numpy as np
import scipy as sp
import itertools
import random

import mpl_toolkits.mplot3d as a3
import matplotlib.colors as colors
import matplotlib.pyplot as plt

class VoronoiMesh(object):

    def tessellate(self, particles):
        """
        create voronoi tesselation from particle positions
        """

        # create the voronoi tessellation
        vor = Voronoi(particles.T)

        num_particles = particles.shape[1]

        # list of lists that holds all neighbors of particles
        neighbor_graph = [[] for i in xrange(num_particles)]

        # list of lists that holds all the indices that make up
        # the faces for a given particle
        face_graph = [[] for i in xrange(num_particles)]

        # list of lists that holds then number of vertices for each
        # face for each particle
        face_graph_sizes = [[] for i in xrange(num_particles)]

        # loop through each face collecting the two particles
        # that make up the face as well as the indices that 
        # make up the face
        for i, face in enumerate(vor.ridge_points):

            p1, p2 = face
            neighbor_graph[p1].append(p2)
            neighbor_graph[p2].append(p1)

            # add indices that make up the face
            face_graph[p1] += vor.ridge_vertices[i]
            face_graph[p2] += vor.ridge_vertices[i]

            # add the number of points that make up the face
            face_graph_sizes[p1].append(len(vor.ridge_vertices[i]))
            face_graph_sizes[p2].append(len(vor.ridge_vertices[i]))

        # sizes for 1d graphs, some particles do not have neighbors (coplanar precission error), these
        # are the outside boundaries which does not cause a problem
        neighbor_graph_sizes = np.array([1 if n == [] else len(n) for n in neighbor_graph], dtype=np.int32)

        # have to clean up the particles that do not have neighbors
        neighbor_graph = [[-1] if n == [] else n for n in neighbor_graph]

        # there elements with no faces, list must have zero size not empty
        # faces need to be cleaned up too
        face_graph = [[-1] if x == [] else x for x in face_graph]
        face_graph_sizes = [[1] if x == [] else x for x in face_graph]

        # graphs in 1d
        neighbor_graph = np.array(list(itertools.chain.from_iterable(neighbor_graph)), dtype=np.int32)
        face_graph = np.array(list(itertools.chain.from_iterable(face_graph)), dtype=np.int32)
        face_graph_sizes = np.array(list(itertools.chain.from_iterable(face_graph_sizes)), dtype=np.int32)

        return neighbor_graph, neighbor_graph_sizes, face_graph, face_graph_sizes, vor.vertices

def test_vol():

    L = 1.0
    n = 10

    dx = L/n
    q = (np.arange(n+6, dtype=np.float64) - 3)*dx + 0.5*dx

    N = q.size
    x = np.zeros(N**3)
    y = np.zeros(N**3)
    z = np.zeros(N**3)

    part = 0
    for i in xrange(N):
        for j in xrange(N):
            for k in xrange(N):
                x[part] = q[i]
                y[part] = q[j]
                z[part] = q[k]
                part += 1

    x += 0.01*dx*(2.0*np.random.random(len(x))-1.0)
    y += 0.01*dx*(2.0*np.random.random(len(y))-1.0)
    z += 0.01*dx*(2.0*np.random.random(len(z))-1.0)

    particles = np.array([x,y,z])
    vor = VoronoiMesh()
    neighbor_graph, neighbor_graph_sizes, face_graph, face_graph_sizes, vertices = vor.tessellate(particles)

    return neighbor_graph, neighbor_graph_sizes, face_graph, face_graph_sizes, vertices, particles.T

def make_vor():

    L = 1.0
    n = 3

    dx = L/n
    q = (np.arange(n+6, dtype=np.float64) - 3)*dx + 0.5*dx

    N = q.size
    x = np.zeros(N**3)
    y = np.zeros(N**3)
    z = np.zeros(N**3)

    part = 0
    for i in xrange(N):
        for j in xrange(N):
            for k in xrange(N):
                x[part] = q[i]
                y[part] = q[j]
                z[part] = q[k]
                part += 1

    k = (((0 < x) & (x < 1)) & ((0 < y) & (y < 1)) & ((0 < z) & (z < 1)))

    x_in = x[k]
    y_in = y[k]
    z_in = z[k]

    x = np.append(x_in, x[~k])
    y = np.append(y_in, y[~k])
    z = np.append(z_in, z[~k])

    particles = np.column_stack((x,y,z))

    vor = Voronoi(particles, qhull_options="v Qbb p Fv")

    neighbors = [[] for i in range(27)]
    for i in range(27):
        for j, face in enumerate(vor.ridge_points):
            if i in face:
                #print j, face, vor.ridge_vertices[j]
                neighbors[i].append(j)

    ax = a3.Axes3D(plt.figure())
    for j in range(27):
        for i in neighbors[j]:
            face = vor.ridge_vertices[i]
            face_verts = vor.vertices[face]

            poly = a3.art3d.Poly3DCollection([face_verts], alpha=0.1)
            poly.set_color(colors.rgb2hex(sp.rand(3)))
            poly.set_edgecolor('k')
            ax.add_collection3d(poly)
#
    ax.set_xlim(0,1)
    ax.set_ylim(0,1)
    ax.set_zlim(0,1)

    plt.show()
    #return vor

def test():

#    particles = np.array([[0,2,0], [1,2,0], [2,2,0],
#        [0,1,0], [1,1,0], [2,1,0],
#        [0,0,0], [1,0,0], [2,0,0],
#        # second level
#        [0,2,1], [1,2,1], [2,2,1],
#        [0,1,1], [1,1,1], [2,1,1],
#        [0,0,1], [1,0,1], [2,0,1],
#        # third level
#        [0,2,2], [1,2,2], [2,2,2],
#        [0,1,2], [1,1,2], [2,1,2],
#        [0,0,2], [1,0,2], [2,0,2]])

    L = 1.0
    n = 3

    dx = L/n
    q = (np.arange(n+3, dtype=np.float64) - 3)*dx + 0.5*dx

    N = q.size
    x = np.zeros(N**3)
    y = np.zeros(N**3)
    z = np.zeros(N**3)
    part = 0
    for i in xrange(N):
        for j in xrange(N):
            for k in xrange(N):
                x[part] = q[i] + 0.01*dx*(2.0*random.random()-1.0)
                y[part] = q[j] + 0.01*dx*(2.0*random.random()-1.0)
                z[part] = q[k] + 0.01*dx*(2.0*random.random()-1.0)
                part += 1

    #particles = np.array([x,y,z])
    particles = np.column_stack((x,y,z))

    #tri = np.array([[-100,-100,-50],
    #    [100,-100,-50],
    #    [-100,100,-50],
    #    [100, 100,-50],
    #    [0,0, 50]])

    #particles = np.vstack((particles, tri))
    #particles = np.transpose(particles)

    #vor = VoronoiMesh()
    #neighbor_graph, neighbor_graph_sizes, face_graph, face_graph_sizes, vertices = vor.tessellate(particles)

    #return neighbor_graph, neighbor_graph_sizes, face_graph, face_graph_sizes, vertices, particles.T
    return particles

if __name__ == "__main__":
    make_vor()
