"""Test the ParticleArrayExchange object with the following data

25 particles are created on a rectangular grid with the following
processor assignment:

2---- 3---- 3---- 3---- 3
|     |     |     |     |
1---- 1---- 1---- 2---- 2
|     |     |     |     |
0---- 0---- 1---- 1---- 1
|     |     |     |     |
0---- 0---- 0---- 0---- 0
|     |     |     |     |
0---- 0---- 0---- 0---- 0


We assume that after a load balancing step, we have the following
distribution:

1---- 1---- 1---- 3---- 3
|     |     |     |     |
1---- 1---- 1---- 3---- 3
|     |     |     |     |
0---- 0---- 0---- 3---- 3
|     |     |     |     |
0---- 0---- 2---- 2---- 2
|     |     |     |     |
0---- 0---- 2---- 2---- 2

We create a ParticleArray to represent the initial distribution and
use ParticleArrayExchange to move the data by manually setting the
particle import/export lists. We require that the test be run with 4
processors.

"""
import mpi4py.MPI as MPI
import numpy as np

from particles.particle_container import ParticleContainer

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()


if size != 4:
    if rank == 0:
        raise RuntimeError("Run this test with 4 processors")

# create the initial distribution
if rank == 0:

    num_particles = 12

    pc = ParticleContainer(num_particles)
    pc['position-x'][:] = np.array( [0.0, 1.0, 2.0, 3.0, 4.0,
                                     0.0, 1.0, 2.0, 3.0, 4.0,
                                     0.0, 1.0] , dtype=np.float64)

    pc['position-y'][:] = np.array( [0.0, 0.0, 0.0, 0.0, 0.0,
                                     1.0, 1.0, 1.0, 1.0, 1.0,
                                     2.0, 2.0] , dtype=np.float64)

    numExport = 6
    exportLocalids = np.array( [2, 3, 4, 7, 8, 9], dtype=np.int32 )
    exportProcs = np.array( [2, 2, 2, 2, 2, 2], dtype=np.int32 )

if rank == 1:

    num_particles = 6

    pc = ParticleContainer(num_particles)
    pc['position-x'][:] = np.array( [2.0, 3.0, 4.0,
                                     0.0, 1.0, 2.0] , dtype=np.float64)

    pc['position-y'][:] = np.array( [2.0, 2.0, 2.0,
                                     3.0, 3.0, 3.0] , dtype=np.float64)

    numExport = 3
    exportLocalids = np.array( [0, 1, 2], dtype=np.int32 )
    exportProcs = np.array( [0, 3, 3], dtype=np.int32 )

if rank == 2:

    num_particles = 3

    pc = ParticleContainer(num_particles)
    pc['position-x'][:] = np.array( [4.0, 3.0, 0.0] , dtype=np.float64)
    pc['position-y'][:] = np.array( [3.0, 3.0, 4.0] , dtype=np.float64)

    numExport = 3
    exportLocalids = np.array( [0, 1, 2], dtype=np.int32 )
    exportProcs = np.array( [3, 3, 1], dtype=np.int32 )

if rank == 3:

    num_particles = 4

    pc = ParticleContainer(num_particles)
    pc['position-x'][:] = np.array( [1.0, 2.0, 3.0, 4.0], dtype=np.float64)
    pc['position-y'][:] = np.array( [4.0, 4.0, 4.0, 4.0], dtype=np.float64)

    numExport = 2
    exportLocalids = np.array( [0,1], dtype=np.int32 )
    exportProcs = np.array( [1, 1], dtype=np.int32 )


comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

# put particles in cpu order
ind = exportProcs.argsort()
exportProcs = exportProcs[ind]
exportLocalids = exportLocalids[ind]

# count the number of particles to send to each process
send_particles = np.bincount(exportProcs, minlength=size).astype(np.int32)

# extract data to send and remove the particles
x_send = pc['position-x'][exportLocalids]
pc.remove_particles(exportLocalids)

# how many particles are being sent from each process
recv_particles = np.empty(size, dtype=np.int32)
comm.Alltoall(sendbuf=send_particles, recvbuf=recv_particles)

# resize arrays to give room for incoming particles
current_size = pc.num_particles
new_size = current_size + np.sum(recv_particles)
pc.resize(new_size)

offset_se = np.zeros(size, dtype=np.int32)
offset_re = np.zeros(size, dtype=np.int32)
for i in range(1,size):
    offset_se[i] = send_particles[i-1] + offset_se[i-1]
    offset_re[i] = recv_particles[i-1] + offset_re[i-1]

ptask = 0
while size > (1<<ptask):
    ptask += 1

for ngrp in xrange(1,1 << ptask):
    sendTask = rank
    recvTask = rank ^ ngrp
    if recvTask < size:
        if send_particles[recvTask] > 0 or recv_particles[recvTask] > 0:

            sendbuf=[x_send,   (send_particles[recvTask], offset_se[recvTask])]
            recvbuf=[pc['position-x'][current_size:], (recv_particles[recvTask], offset_re[recvTask])]

            comm.Sendrecv(sendbuf=sendbuf, dest=recvTask, recvbuf=recvbuf, source=recvTask)

print "rank %d: %s" % (rank, pc['position-x'][current_size:])