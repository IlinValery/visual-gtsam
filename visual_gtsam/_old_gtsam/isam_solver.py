import gtsam
import numpy as np
from gtsam.gtsam import NonlinearFactorGraph

from data_generation.utils import wrap_angle


class IsamSolver:

    def __init__(self, initial_state, covariance, alphas, beta):
        self._initial_state = gtsam.Pose2(initial_state[0], initial_state[1], initial_state[2])
        self._prior_noise = gtsam.noiseModel_Diagonal.Sigmas(np.array([covariance, covariance, covariance]))
        # self.observation_noise = gtsam.noiseModel_Diagonal.Sigmas(np.array([beta[0] ** 2, np.deg2rad(beta[1]) ** 2]))
        #self.observation_noise = gtsam.noiseModel_Diagonal.Sigmas(np.array([beta[0] ** 2, np.deg2rad(beta[1]) ** 2]))
        self.observation_noise = gtsam.noiseModel_Diagonal.Sigmas(
            np.array(([np.deg2rad(beta[1]) ** 2, (beta[0] / 100) ** 2])))
        self.beta = beta
        self.alphas = alphas ** 2
        self.pose_num = 0
        self.observation_num = 1000
        self.landmark_indexes = list()
        self.states_new = np.array([[]])
        self.observation_new = np.array([[]])

        self.graph = gtsam.NonlinearFactorGraph()
        self.estimations = gtsam.Values()
        self.result = gtsam.Values()
        self.parameters = gtsam.ISAM2Params()
        self.parameters.setRelinearizeThreshold(1e-4)
        self.parameters.setRelinearizeSkip(1)
        self.slam = gtsam.ISAM2(self.parameters)

        self.graph.add(gtsam.PriorFactorPose2(self.pose_num, self._initial_state, self._prior_noise))
        self.estimations.insert(self.pose_num, self._initial_state)

    @staticmethod
    def _get_motion_prediction(state, motion):
        """
            Predicts the next state given state and the motion command.
        """
        x = state.x()
        y = state.y()
        theta = state.theta()

        drot1, dtran, drot2 = motion

        theta += drot1
        x += dtran * np.cos(theta)
        y += dtran * np.sin(theta)
        theta += drot2

        # Wrap the angle between [-pi, +pi].
        theta = wrap_angle(theta)

        return gtsam.Pose2(x, y, theta)

    @staticmethod
    def _get_motion_noise_covariance(motion, alphas):

          drot1, dtran, drot2 = motion
          a1, a2, a3, a4 = alphas

          return np.array([a1 * drot1 ** 2 + a2 * dtran ** 2,
                    a3 * dtran ** 2 + a4 * (drot1 ** 2 + drot2 ** 2),
                    a1 * drot2 ** 2 + a2 * dtran ** 2])

    @staticmethod
    def _get_landmark_position(state, distance, bearing):
        """
            Predicts the landmark position based on a current state and observation distance and bearing.
        """
        angle = wrap_angle(state.theta() + bearing)
        x_relative = distance * np.cos(angle)
        y_relative = distance * np.sin(angle)
        x = x_relative + state.x()
        y = y_relative + state.y()

        return gtsam.Point2(x, y)

    @staticmethod
    def _get_motion_gtsam_format(motion):
        """
            Predicts the landmark position based on a current state and observation distance and bearing.
        """
        drot1, dtran, drot2 = motion

        theta = drot1 + drot2
        x = dtran * np.cos(theta)
        y = dtran * np.sin(theta)

        # Wrap the angle between [-pi, +pi].
        theta = wrap_angle(theta)

        return gtsam.Pose2(x, y, theta)

    def _convert_to_np_format(self):
        """
            Converts from gtsam.Pose2 to numpy format.
        """
        states = list()
        landmarks = list()
        for i in range(self.pose_num):
            states.append([self.result.atPose2(i).x(), self.result.atPose2(i).y()])

        for i in range(1000, self.observation_num):
            landmarks.append([self.result.atPoint2(i).x(), self.result.atPoint2(i).y()])

        self.states_new = np.array(states)
        self.observation_new = np.array(landmarks)

    def update(self, motion, measurement):

        if self.pose_num == 0:
            self.result = self.estimations

        odometry = self._get_motion_gtsam_format(motion)
        noise = gtsam.noiseModel_Diagonal.Sigmas(self._get_motion_noise_covariance(motion, self.alphas))

        predicted_state = self._get_motion_prediction(self.result.atPose2(self.pose_num), motion)

        # adding to the graph odometry value
        self.graph.add(gtsam.BetweenFactorPose2(self.pose_num, self.pose_num + 1, odometry, noise))
        # adding predicted pose to the initial estimations
        self.estimations.insert(self.pose_num + 1, predicted_state)

        for i in range(len(measurement)):
            bearing = gtsam.Rot2(measurement[i, 1])
            distance = measurement[i, 0]
            landmark_id = self.observation_num

            # adding to the graph measurement value
            self.graph.add(
                gtsam.BearingRangeFactor2D(self.pose_num, landmark_id, bearing, distance, self.observation_noise))
            landmark_position = self._get_landmark_position(self.result.atPose2(self.pose_num), distance,
                                                            bearing.theta())

            # adding predicted landmarks position to the initial estimations
            self.estimations.insert(landmark_id, landmark_position)
            self.observation_num += 1

        """
        for i in range(len(measurement)):

            bearing = gtsam.Rot2(measurement[i, 0])
            distance = measurement[i, 1]
            landmark_id = 1000 + measurement[i, 2]

            if landmark_id not in self.landmark_indexes:
                self.landmark_indexes.append(landmark_id)
                landmark_position = self._get_landmark_position(self.result.atPose2(self.pose_num), distance, bearing.theta())
                self.graph.add(gtsam.BearingRangeFactor2D(self.pose_num, landmark_id, bearing, distance, self.observation_noise))
                self.estimations.insert(landmark_id, landmark_position)
            else:
                pass
        """

        # update factorization problem
        #print(noise)
        #print(self.observation_noise)
        print(self.estimations)

        #params = gtsam.LevenbergMarquardtParams()
        #optimiser = gtsam.LevenbergMarquardtOptimizer(self.graph, self.estimations, params)
        #optimiser.optimize()

        self.slam.update(self.graph, self.estimations)

        # clearing current graph and estimations
        self.graph.resize(0)
        self.estimations.clear()
        print(self.graph)

        # getting results
        self.result = self.slam.calculateEstimate()
        #print(self.result)

        self.pose_num += 1
        self._convert_to_np_format()
