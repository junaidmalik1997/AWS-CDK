### This file creates an ecs cluster with one task definition containing 2 containers, Both containers are ###
### mounted with same efs volume. Writer container creates a text file inside volume while reader container ##
### can read that file. This document also contains dockerfiles for both containers. ###

import aws_cdk as cdk
from constructs import Construct

import aws_cdk.aws_ecs as ecs
import aws_cdk.aws_ecs_patterns as ecsp
import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_efs as efs
import aws_cdk.aws_iam as iam
import aws_cdk.aws_stepfunctions_tasks as tasks
import aws_cdk.aws_stepfunctions as sfn


class EcsStack(cdk.Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)


        ### creates a vpc ###
        vpc = ec2.Vpc(self, "TheVPC",
            cidr="10.0.0.0/16"
        )
        ### Iterate the private subnets ###
        selection = vpc.select_subnets(
            subnet_type=ec2.SubnetType.PRIVATE_WITH_NAT
            )
        for subnet in selection.subnets:
            pass
        
        ### Creates an ECS Cluster ###
        cluster = ecs.Cluster(self, "Cluster",
            vpc=vpc
        )    
        
        ### Security Group ###
        security_group = ec2.SecurityGroup(
            self, "WSSG",
            vpc=vpc,
            allow_all_outbound=True
        )
        security_group.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(80)
        )        
        security_group.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(22)
        ) 
        security_group.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(2049)              ### Port for efs volume ###
        ) 


        ### File System ###
        file_system = efs.FileSystem(self, "EFS",
            vpc=vpc,
            file_system_name="junaidd-efs",
            lifecycle_policy=efs.LifecyclePolicy.AFTER_14_DAYS,  
            performance_mode=efs.PerformanceMode.GENERAL_PURPOSE,
            out_of_infrequent_access_policy=efs.OutOfInfrequentAccessPolicy.AFTER_1_ACCESS,
            security_group=security_group,
            removal_policy=cdk.RemovalPolicy.DESTROY

        )
        

        ### Volume ###
        volume = ecs.Volume(
            name="mydatavolume",
            efs_volume_configuration=ecs.EfsVolumeConfiguration(
            file_system_id=file_system.file_system_id
            )
        )


        ### Creates a mount point ###
        mount_point = ecs.MountPoint(
            container_path="/myvol",
            read_only=False,
            source_volume="mydatavolume"
        )
        

        ### Task definition ###
        fargate_task_definition = ecs.FargateTaskDefinition(self, "TaskDef",
            memory_limit_mib=1024,
            cpu=512,
            volumes=[volume]
        )


        ### Container Definition ###
        container_definition = fargate_task_definition.add_container("WriterContainer",
            # Use an image from ECR
            image=ecs.EcrImage.from_registry("public.ecr.aws/y2a9o9h4/junaid4:latest"), ### Link to ECR image ###
            # image=ecs.ContainerImage.from_registry("httpd"),
            memory_limit_mib=256,
            cpu=128,
            logging=ecs.LogDriver.aws_logs(stream_prefix="krs-poc-logs")

        )


        ### Mounts volume with Container ###
        container_definition.add_mount_points(mount_point)


        ### 2nd Container Definition ###
        container_definition_2 = fargate_task_definition.add_container("readerContainer",
            # Use an image from ECR
            image=ecs.EcrImage.from_registry("public.ecr.aws/y2a9o9h4/junaid5:latest"), ### ECR Image URI ###
            # Use an image from Dockerhub
            # image=ecs.ContainerImage.from_registry("httpd"),
            memory_limit_mib=256,
            cpu=128,
            logging=ecs.LogDriver.aws_logs(stream_prefix="krs-poc-logs2")

        )

        ### Mounts container ###
        container_definition_2.add_mount_points(mount_point)


        ### Creates a Service ###       
        service = ecs.FargateService(self, "Service",
            cluster=cluster,
            task_definition=fargate_task_definition,
            desired_count=0, ### Change it to one from aws console once everything is deployed ###
            security_groups=[security_group]
        )

        
### Writer container dockerfile
FROM ubuntu
RUN mkdir myvol
VOLUME /myvol
ENTRYPOINT ["/bin/sh","-c"]
CMD ["echo \"HELLO WORLD\" > newefs && mv newefs myvol/ &&ls -la myvol && cat /myvol/newefs"]


### Reader Container Dockerfile
FROM ubuntu
RUN mkdir myvol
VOLUME /myvol
ENTRYPOINT ["/bin/sh","-c"]
CMD ["ls && cat /myvol/newefs" ]
