import time

import torch
import utils
from torch.nn.utils import parameters_to_vector
from torch.utils.data import DataLoader


class Agent():
    def __init__(self, id, args, train_dataset=None, data_idxs=None, mask=None):
        self.id = id
        self.args = args
        self.error = 0
        # get datasets, fedemnist is handled differently as it doesn't come with pytorch
        if train_dataset is None:
            self.train_dataset = torch.load(f'../data/Fed_EMNIST/user_trainsets/user_{id}_trainset.pt')

            # for backdoor attack, agent poisons his local dataset
            if self.id < args.num_corrupt:
                utils.poison_dataset(self.train_dataset, args, data_idxs, agent_idx=self.id)

        else:
            if self.args.data!= "tinyimagenet":
                self.train_dataset = utils.DatasetSplit(train_dataset, data_idxs)
                # for backdoor attack, agent poisons his local dataset
                if self.id < args.num_corrupt:
                    utils.poison_dataset(train_dataset, args, data_idxs, agent_idx=self.id)
            else:
                self.train_dataset = utils.DatasetSplit(train_dataset, data_idxs, runtime_poison=True, args=args, client_id =id)
        # get dataloader
        self.train_loader = DataLoader(self.train_dataset, batch_size=self.args.bs, shuffle=True, \
                                       num_workers=args.num_workers, pin_memory=False , drop_last=True)
        # size of local dataset
        self.n_data = len(self.train_dataset)





    def local_train(self, global_model, criterion, round=None):
        """ Do a local training over the received global model, return the update """
        initial_global_model_params = parameters_to_vector([ global_model.state_dict()[name] for name in global_model.state_dict()]).detach()
        # initial_global_model_params_local = parameters_to_vector(global_model.parameters()).detach()
        # if  self.id<self.args.num_corrupt and self.mask_update!= None:
        #     initial_global_model_params_local = self.mask_update.to(self.args.device) + initial_global_model_params.to(self.args.device) * (1-self.previous_mask.to(self.args.device))
        #     vector_to_parameters(initial_global_model_params_local, global_model.parameters())

        global_model.train()
        optimizer = torch.optim.SGD(global_model.parameters(), lr=self.args.client_lr* (self.args.lr_decay)**round, weight_decay=self.args.wd)
        for _ in range(self.args.local_ep):
            start = time.time()
            for _, (inputs, labels) in enumerate(self.train_loader):
                optimizer.zero_grad()
                inputs, labels = inputs.to(device=self.args.device, non_blocking=True), \
                                 labels.to(device=self.args.device, non_blocking=True)
                outputs = global_model(inputs)
                minibatch_loss = criterion(outputs, labels)
                minibatch_loss.backward()
                optimizer.step()
            end = time.time()
            print(end-start)

        with torch.no_grad():
            after_train = parameters_to_vector([ global_model.state_dict()[name] for name in global_model.state_dict()]).detach()
            self.update = after_train- initial_global_model_params
            return self.update
