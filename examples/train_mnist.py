"""Yaspi example:
Aims to be a minimal modification to the PyTorch MNIST example given here:
https://github.com/pytorch/examples/blob/master/mnist/main.py

Example usage
---------------

- Standard training:
    python train_mnist.py

- Yaspi training:
    python train_mnist.py --hyperparams mnist_hyperparams.json --yaspify
   (this launches one run for each experiment config defined in mnist_hyperparams.json)
"""
import argparse
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torchvision import datasets, transforms
from torch.optim.lr_scheduler import StepLR
import sys
import json
from yaspi.yaspi import Yaspi


class Net(nn.Module):
    def __init__(self):
        super(Net, self).__init__()
        self.conv1 = nn.Conv2d(1, 32, 3, 1)
        self.conv2 = nn.Conv2d(32, 64, 3, 1)
        self.dropout1 = nn.Dropout(0.25)
        self.dropout2 = nn.Dropout(0.5)
        self.fc1 = nn.Linear(9216, 128)
        self.fc2 = nn.Linear(128, 10)

    def forward(self, x):
        x = self.conv1(x)
        x = F.relu(x)
        x = self.conv2(x)
        x = F.relu(x)
        x = F.max_pool2d(x, 2)
        x = self.dropout1(x)
        x = torch.flatten(x, 1)
        x = self.fc1(x)
        x = F.relu(x)
        x = self.dropout2(x)
        x = self.fc2(x)
        output = F.log_softmax(x, dim=1)
        return output


def train(args, model, device, train_loader, optimizer, epoch):
    model.train()
    for batch_idx, (data, target) in enumerate(train_loader):
        data, target = data.to(device), target.to(device)
        optimizer.zero_grad()
        output = model(data)
        loss = F.nll_loss(output, target)
        loss.backward()
        optimizer.step()
        if batch_idx % args.log_interval == 0:
            print('Train Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(
                epoch, batch_idx * len(data), len(train_loader.dataset),
                100. * batch_idx / len(train_loader), loss.item()))
            if args.dry_run:
                break


def test(model, device, test_loader):
    model.eval()
    test_loss = 0
    correct = 0
    with torch.no_grad():
        for data, target in test_loader:
            data, target = data.to(device), target.to(device)
            output = model(data)
            test_loss += F.nll_loss(output, target, reduction='sum').item()  # sum up batch loss
            pred = output.argmax(dim=1, keepdim=True)  # get the index of the max log-probability
            correct += pred.eq(target.view_as(pred)).sum().item()

    test_loss /= len(test_loader.dataset)

    print('\nTest set: Average loss: {:.4f}, Accuracy: {}/{} ({:.0f}%)\n'.format(
        test_loss, correct, len(test_loader.dataset),
        100. * correct / len(test_loader.dataset)))


def main():
    # Training settings
    parser = argparse.ArgumentParser(description='PyTorch MNIST Example')
    parser.add_argument('--batch-size', type=int, default=64, metavar='N',
                        help='input batch size for training (default: 64)')
    parser.add_argument('--test-batch-size', type=int, default=1000, metavar='N',
                        help='input batch size for testing (default: 1000)')
    parser.add_argument('--epochs', type=int, default=14, metavar='N',
                        help='number of epochs to train (default: 14)')
    parser.add_argument('--lr', type=float, default=1.0, metavar='LR',
                        help='learning rate (default: 1.0)')
    parser.add_argument('--gamma', type=float, default=0.7, metavar='M',
                        help='Learning rate step gamma (default: 0.7)')
    parser.add_argument('--no-cuda', action='store_true', default=False,
                        help='disables CUDA training')
    parser.add_argument('--dry-run', action='store_true', default=False,
                        help='quickly check a single pass')
    parser.add_argument('--seed', type=int, default=1, metavar='S',
                        help='random seed (default: 1)')
    parser.add_argument('--log-interval', type=int, default=10, metavar='N',
                        help='how many batches to wait before logging training status')
    parser.add_argument('--save-model', action='store_true', default=False,
                        help='For Saving the current Model')

    # Additional flags used by yaspi
    parser.add_argument("--yaspify", action="store_true")
    parser.add_argument("--yaspi_settings", default="yaspi_settings.json",
                        help="file of SLURM specific options (e.g. number of GPUS)")
    parser.add_argument("--hyperparams", default="mnist_hyperparams.json")
    args = parser.parse_args()

    if args.yaspify:
        # --------------------------------------------------------------------
        # This section contains the logic for launching multiple runs
        # --------------------------------------------------------------------
        # The command that will be launched on each worker will be identical to the
        # python command used to launch this script (including all flags), except:
        #  1. The --yaspify flag will be removed
        #  2. Flags from hyperparams will be inserted
        # -------------------------------------------------------------------------

        # load the hyperparameters
        with open(args.hyperparams, "r") as f:
            hyperparams = json.load(f)
        exp_flags = []
        for exp in hyperparams:
            exp_flags.append(" ".join([f"--{key} {val}" for key, val in exp.items()]))

        # Select a name for your jobs (this is what will be visible via the `sinfo`
        # SLURM command)
        num_jobs = len(exp_flags)
        job_name = f"train-mnist-{num_jobs}-jobs"

        # Provide the arguments to each SLURM worker as space-separated quoted strings
        job_queue = " ".join([f'"{flags}"' for flags in exp_flags])

        # remove the yaspify flag
        cmd_args = sys.argv
        cmd_args.remove("--yaspify")

        # construct the final command that will run each worker, together with job_queue
        base_cmd = f"python {' '.join(cmd_args)}"

        # load SLURM specific settings
        with open(args.yaspi_settings, "r") as f:
            yaspi_defaults = json.load(f)

        # Launch the jobs over SLURM
        job = Yaspi(
            cmd=base_cmd,
            job_queue=job_queue,
            job_name=job_name,
            job_array_size=num_jobs,
            **yaspi_defaults,
        )
        # The `watch` argument will keep 
        job.submit(watch=True, conserve_resources=5)
    else:
        # --------------------------------------------------------------------
        # This section contains the original, unmodified code
        # --------------------------------------------------------------------
        use_cuda = not args.no_cuda and torch.cuda.is_available()
        torch.manual_seed(args.seed)

        device = torch.device("cuda" if use_cuda else "cpu")

        train_kwargs = {'batch_size': args.batch_size}
        test_kwargs = {'batch_size': args.test_batch_size}
        if use_cuda:
            cuda_kwargs = {'num_workers': 1,
                        'pin_memory': True,
                        'shuffle': True}
            train_kwargs.update(cuda_kwargs)
            test_kwargs.update(cuda_kwargs)

        transform=transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize((0.1307,), (0.3081,))
            ])
        dataset1 = datasets.MNIST('../data', train=True, download=True,
                        transform=transform)
        dataset2 = datasets.MNIST('../data', train=False,
                        transform=transform)
        train_loader = torch.utils.data.DataLoader(dataset1,**train_kwargs)
        test_loader = torch.utils.data.DataLoader(dataset2, **test_kwargs)

        model = Net().to(device)
        optimizer = optim.Adadelta(model.parameters(), lr=args.lr)

        scheduler = StepLR(optimizer, step_size=1, gamma=args.gamma)
        for epoch in range(1, args.epochs + 1):
            train(args, model, device, train_loader, optimizer, epoch)
            test(model, device, test_loader)
            scheduler.step()

        if args.save_model:
            torch.save(model.state_dict(), "mnist_cnn.pt")

if __name__ == '__main__':
    main()
