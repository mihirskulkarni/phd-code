import h5py
import numpy as np
from PHD.fields import Fields
from PHD.mesh import VoronoiMesh
from PHD.riemann.riemann_base import RiemannBase
from PHD.boundary.boundary_base import BoundaryBase
from PHD.reconstruction.reconstruct_base import ReconstructBase

# for debug plotting 
from matplotlib.collections import LineCollection, PolyCollection, PatchCollection
from matplotlib.patches import Polygon
import matplotlib.pyplot as plt
import matplotlib


class MovingMesh(object):

    def __init__(self, gamma = 1.4, CFL = 0.5, max_steps=100, max_time=None, output_cycle = 100000,
            output_name="simulation_", regularization=True):

        # simulation parameters
        self.CFL = CFL
        self.gamma = gamma
        self.max_steps = max_steps
        self.max_time = max_time
        self.output_cycle = output_cycle
        self.output_name = output_name
        self.regularization = regularization

        # particle information
        self.particles = None
        self.fields = None
        self.cell_info = None

        self.particles_index = None
        self.voronoi_vertices = None
        self.neighbor_graph = None
        self.neighbor_graph_sizes = None
        self.face_graph = None
        self.face_graph_sizes = None

        self.time = 0.

        # simulation classes
        self.mesh = VoronoiMesh()
        self.boundary = None
        self.reconstruction = None
        self.riemann_solver = None


    def get_dt(self):
        """
        Calculate the time step using the CFL condition.
        """

        vol = self.cell_info["volume"]

        # grab values that correspond to real particles
        dens = self.fields.get_field("density")
        velx = self.fields.get_field("velocity-x")
        vely = self.fields.get_field("velocity-x")
        pres = self.fields.get_field("pressure")

        # sound speed
        c = np.sqrt(self.gamma*pres/dens)

        # calculate approx radius of each voronoi cell
        R = np.sqrt(vol/np.pi)

        u = np.sqrt(velx**2 + vely**2)

        # largest eigenvalue
        lam = np.maximum.reduce([np.absolute(u-c), np.absolute(u), np.absolute(u+c)])

        self.dt = self.CFL*np.min(R/lam)

        if self.time + self.dt > self.max_time:
            self.dt = self.max_time - self.time


    def data_dump(self, num):

        f = h5py.File(self.output_name + "_" + `num`.zfill(4) + ".hdf5", "w")

        dens = self.fields.get_field("density")
        velx = self.fields.get_field("velocity-x")
        vely = self.fields.get_field("velocity-y")
        pres = self.fields.get_field("pressure")

        f["/particles"]  = self.particles

        f["/density"]    = dens
        f["/velocity-x"] = velx
        f["/velocity-y"] = vely
        f["/pressure"]   = pres

        f.attrs["time"] = self.time

        f.close()


    def set_boundary_condition(self, boundary):

        if isinstance(boundary, BoundaryBase):
            self.boundary = boundary
        else:
            raise TypeError

    def set_reconstruction(self, reconstruction):

        if isinstance(reconstruction, ReconstructBase):
            self.reconstruction = reconstruction
        else:
            raise TypeError

    def set_initial_state(self, initial_particles, initial_data, initial_particles_index):
        """
        Set the initial state of the system by specifying the particle positions, their data
        U=(density, density*velocity, Energy) and particle labels (ghost or real).

        Parameters
        ----------
        initial_particles : Numpy array of size (dimensino, number particles)
        initial_data : Numpy array of conservative state vector U=(density, density*velocity, Energy)
            with size (variables, number particles)
        initial_particles_index: dictionary with two keys "real" and "ghost" that hold the indices
            in integer numpy arrays of real and ghost particles in the initial_particles array.
        """
        self.particles = initial_particles.copy()
        self.particles_index = dict(initial_particles_index)

        # make initial tesellation
        self.neighbor_graph, self.neighbor_graph_sizes, self.face_graph, self.face_graph_sizes, self.voronoi_vertices = self.mesh.tessellate(self.particles)

        # calculate volume of real particles 
        self.cell_info = self.mesh.volume_center_mass(self.particles, self.neighbor_graph, self.neighbor_graph_sizes, self.face_graph,
                self.voronoi_vertices, self.particles_index)

        num_particles = self.particles_index["real"].size

        # setup data container
        self.fields = Fields(num_particles, self.gamma, self.boundary)
        self.fields.create_fields()

        mass = self.fields.get_field("mass")
        momx = self.fields.get_field("momentum-x")
        momy = self.fields.get_field("momentum-y")
        ener = self.fields.get_field("energy")

        vol = self.cell_info["volume"]

        mass[:] = initial_data[0,:] * vol
        momx[:] = initial_data[1,:] * vol
        momy[:] = initial_data[2,:] * vol
        ener[:] = initial_data[3,:] * vol


    def set_riemann_solver(self, riemann_solver):

        if isinstance(riemann_solver, RiemannBase):
            self.riemann_solver = riemann_solver
        else:
            raise TypeError("Unknown riemann solver")

    def set_parameter(self, parameter_name, parameter):

        if parameter_name in self.__dict__.keys():
            setattr(self, parameter_name, parameter)
        else:
            raise ValueError("Unknown parameter: %s" % parameter_name)

    def solve(self):
        """
        Evolve the simulation from time zero to the specified max time.
        """
        num_steps = 0

        while self.time < self.max_time and num_steps < self.max_steps:


            self._solve_one_step(num_steps)
            self.time += self.dt

            print "solving for step:", num_steps, "time: ", self.time


            # output data
            if num_steps%self.output_cycle == 0:
                self.data_dump(num_steps)

            num_steps+=1

#            # debugging plot --- turn to a routine later ---
#            l = []
#            ii = 0; jj = 0
#            for ip in self.particles_index["real"]:
#
#                jj += self.neighbor_graph_sizes[ip]*2
#                verts_indices = np.unique(self.face_graph[ii:jj])
#                verts = self.voronoi_vertices[verts_indices]
#
#                # coordinates of neighbors relative to particle p
#                xc = verts[:,0] - self.particles[0,ip]
#                yc = verts[:,1] - self.particles[1,ip]
#
#                # sort in counter clock wise order
#                sorted_vertices = np.argsort(np.angle(xc+1j*yc))
#                verts = verts[sorted_vertices]
#
#                l.append(Polygon(verts, True))
#
#                ii = jj
#
#
#            cells = self.particles_index["real"]
#            dens = self.fields.get_field("density")
#            velx = self.fields.get_field("velocity-x")
#            vely = self.fields.get_field("velocity-y")
#            pres = self.fields.get_field("pressure")
#
#            # add colormap
#            colors = []
#            for i in self.particles_index["real"]:
#                colors.append(dens[i])
#
#            #fig, ax = plt.subplots(figsize=(20, 5))
#            fig, ax = plt.subplots()
#            p = PatchCollection(l, alpha=0.4)
#            p.set_array(np.array(colors))
#            p.set_clim([0, 4])
#
#            ax.set_xlim(0,2)
#            ax.set_ylim(0,0.2)
#            ax.set_aspect(2)
#            ax.add_collection(p)
#
#            plt.colorbar(p, orientation='horizontal')
#            plt.savefig(self.output_name+`num_steps`.zfill(4))
#            plt.clf()
#
#
#
#            plt.figure(figsize=(5,5))
#            plt.subplot(3,1,1)
#            plt.scatter(self.particles[0,cells], dens, facecolors="none", edgecolors="r")
#            #plt.xlim(-0.2,2.2)
#            plt.ylim(0,1.1)
#
#            plt.subplot(3,1,2)
#            plt.scatter(self.particles[0,cells], velx, facecolors="none", edgecolors="r")
#            #plt.xlim(-0.2,2.2)
#            plt.ylim(-0.1,1.1)
#
#            plt.subplot(3,1,3)
#
#            plt.scatter(self.particles[0,cells], pres, facecolors="none", edgecolors="r")
#            #plt.xlim(-0.2,2.2)
#            plt.ylim(-0.1,1.1)
#
#            plt.savefig("scatter"+`num_steps`.zfill(4))
#            plt.clf()

        # last data dump
        self.data_dump(num_steps)


    def _solve_one_step(self, count):
        """
        Evolve the simulation for one time step.
        """

        # generate ghost particles with links to original real particles 
        self.particles = self.fields.update_boundaries(self.particles, self.particles_index, self.neighbor_graph, self.neighbor_graph_sizes)

        # construct the new mesh 
        self.neighbor_graph, self.neighbor_graph_sizes, self.face_graph, self.face_graph_sizes, self.voronoi_vertices = self.mesh.tessellate(self.particles)

        # calculate volume and center of mass of real particles
        self.cell_info = self.mesh.volume_center_mass(self.particles, self.neighbor_graph, self.neighbor_graph_sizes, self.face_graph,
                self.voronoi_vertices, self.particles_index)

        # calculate primitive variables of real particles
        self.fields.update_primitive(self.cell_info["volume"], self.particles, self.particles_index)

        # calculate global time step from real particles
        self.get_dt()

        # assign fluid velocities to particles
        w = self.mesh.assign_particle_velocities(self.particles, self.fields.prim, self.particles_index, self.cell_info, self.gamma, self.regularization)

        # grab left and right states for each face
        faces_info = self.mesh.faces_for_flux(self.particles, self.fields.prim, w, self.particles_index, self.neighbor_graph,
                self.neighbor_graph_sizes, self.face_graph, self.voronoi_vertices)

        # calculate gradient for real particles
        self.reconstruction.gradient(self.fields.prim, self.particles, self.particles_index, self.cell_info, self.neighbor_graph, self.neighbor_graph_sizes,
                self.face_graph, self.voronoi_vertices)

        # calculate state at face by riemann solver
        fluxes = self.riemann_solver.fluxes(faces_info, self.gamma, self.dt, self.cell_info, self.particles_index)

        # update conserved variables
        self.update(fluxes, faces_info)

        # update particle positions
        self.move_particles():


    def move_particles(self):
        self.particles[:,self.particles_index["real"]] += self.dt*w[:, self.particles_index["real"]]


    def update(self, fluxes, faces_info):

        ghost_map = self.particles_index["ghost_map"]
        area = faces_info["face areas"]

        k = 0
        for i, j in zip(faces_info["face pairs"][0,:], faces_info["face pairs"][1,:]):

            self.fields.field_data[:,i] -= self.dt*area[k]*fluxes[:,k]

            # do not update ghost particle cells
            if not ghost_map.has_key(j):
                self.fields.field_data[:,j] += self.dt*area[k]*fluxes[:,k]

            k += 1
