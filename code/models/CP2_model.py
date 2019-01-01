import tensorflow as tf
import torch as t
from base.base_model import BaseModel


class CP2Model(BaseModel):
    def __init__(self, config):
        super(CP2Model, self).__init__(config)
        self.build_model()
        self.init_saver()

    def build_model(self):
        try:
            if self.config.use_weighted_loss:
                pass
        except AttributeError:
            print('WARN: use_weighted_loss not set - using False')
            self.config.use_weighted_loss = False
        self.is_training = tf.placeholder(tf.bool)
        self.class_weights = tf.placeholder(
            tf.float32, shape=[1, 28], name="weights")
        self.input = tf.placeholder(
            tf.float32, shape=[None, 4, 512, 512], name="input")
        self.label = tf.placeholder(tf.float32, shape=[None, 28])

        # All tf functions work better with channel first
        # otherwise some fail on CPU (known issue)
        x = tf.transpose(self.input, perm=[0, 2, 3, 1])
        # Block 1
        x = tf.layers.conv2d(x, 64, 3, padding='same', name='conv1_1')
        x = tf.nn.relu(x, name='act1_1')
        x = tf.layers.max_pooling2d(
            x, pool_size=(2, 2), strides=(2, 2), name='pool1')
        # Block 2
        x = tf.layers.conv2d(x, 128, 3, padding='same', name='conv2_1')
        x = tf.nn.relu(x, name='act2_1')
        x = tf.layers.max_pooling2d(
            x, pool_size=(2, 2), strides=(2, 2), name='pool2')
        # Classification block
        x = tf.layers.flatten(x, name='flatten')
        x = tf.nn.relu(x, name='act4')
        logits = tf.layers.dense(x, units=28, name='logits')
        out = tf.nn.sigmoid(logits, name='out')
        with tf.name_scope("loss"):
            if self.config.focalLoss:
                self.loss = tf.reduce_mean(focalLoss(input=logits, target=self.label, gamma=2))
            elif self.config.use_weighted_loss:
                tf.stop_gradient(self.class_weights, name="stop_gradient")
                self.loss = tf.losses.compute_weighted_loss(
                    tf.nn.sigmoid_cross_entropy_with_logits(
                        labels=self.label, logits=logits),
                    weights=self.class_weights)
            else:
                self.loss = tf.reduce_mean(
                    tf.nn.sigmoid_cross_entropy_with_logits(
                        labels=self.label, logits=logits))
            self.train_step = tf.train.AdamOptimizer(
                self.config.learning_rate).minimize(
                    self.loss, global_step=self.global_step_tensor)
        with tf.name_scope("output"):
            self.prediction = tf.round(out, name="prediction")

    def init_saver(self):
        # here you initialize the tensorflow saver that will be used
        # in saving the checkpoints.
        self.saver = tf.train.Saver(max_to_keep=self.config.max_to_keep)

# from https://www.kaggle.com/iafoss/pretrained-resnet34-with-rgby-0-460-public-lb
def focalLoss(input, target, gamma=2):
    print(type(input))
    print(tf.__version__)
    #if not (target.size() == input.size()):
    #    raise ValueError("Target size ({}) must be the same as input size ({})"
    #                     .format(target.size(), input.size()))

    max_val = tf.clip_by_value((-input), clip_value_min=0, clip_value_max=(-input))
    loss = input - input * target + max_val + (tf.exp(-max_val) + tf.log(tf.exp((-input - max_val))))

    invprobs = tf.log_sigmoid(-input * (target * 2.0 - 1.0))
    loss = tf.exp((invprobs * gamma)) * loss
    print(loss)

    return tf.reduce_sum(loss)